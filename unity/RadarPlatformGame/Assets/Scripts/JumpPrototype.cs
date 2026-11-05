using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

// Boş bir GameObject'e eklenir. Sahne yalnız Play sırasında oluşturulur.
// Unity 6 içindir; radar girdisi fiziksel zıplama değil, deneysel hareket adayıdır.
[DisallowMultipleComponent]
public class JumpPrototype : MonoBehaviour
{
    // SerializeField, private bir değişkeni Unity Inspector'da düzenlenebilir yapar.
    // Sahneye kaydettiğin Inspector değeri, buradaki başlangıç değerinden önceliklidir.
    // Ayarları Play kapalıyken değiştirip sahneyi Ctrl+S ile kaydet.
    [SerializeField] private int udpPort = 5065;
    [Header("API bağlantısı")]
    [Tooltip("PowerShell'de çalışan ASP.NET Core API adresi.")]
    [SerializeField] private string apiBaseUrl = "http://localhost:5269";
    [SerializeField, InspectorName("Otomatik ilerleme")] private bool autoRun = true;
    [Header("Hareket ayarları")]
    // Dünya birimi/saniye. 5.2 değeri, kareyi her saniye 5.2 birim ilerletir.
    [SerializeField, Min(0), InspectorName("İlerleme hızı")] private float moveSpeed = 5.2f;
    // Dünya birimi/saniye cinsinden ilk yukarı hız. Bu değer doğrudan yükseklik değildir.
    // Yaklaşık yükselme miktarı = jumpSpeed² / (2 * yerçekimi ivmesinin büyüklüğü).
    [Tooltip("İlk dikey hız. Artırınca kare daha yükseğe zıplar.")]
    [SerializeField, Min(0.1f), InspectorName("Zıplama gücü")] private float jumpSpeed = 11.5f;
    // Dikey ivme = Physics2D.gravity.y * gravityScale.
    // Örneğin dünya yerçekimi -9.81 ise 2.5 çarpanı yaklaşık -24.53 birim/saniye² verir.
    [Tooltip("Yerçekimi çarpanı. Artırınca kare daha çabuk düşer, aynı güçle daha az yükselir.")]
    [SerializeField, Min(0.1f), InspectorName("Yerçekimi çarpanı")] private float gravityScale = 2.5f;
    [Header("Cyberpunk renkleri")]
    [InspectorName("Kare kenar ışığı")]
    [SerializeField] private Color squareNeon = new Color(0.12f, 0.95f, 0.9f);
    [InspectorName("Kare iç dolgusu")]
    [SerializeField] private Color squareBody = new Color(0.38f, 0.48f, 0.52f);
    // Zemin dolgusu ve kamera arka planı aynı renk değişkenini kullanır.
    [InspectorName("Arka plan ve zemin")]
    [SerializeField] private Color backgroundColor = new Color(0.035f, 0.025f, 0.09f);
    [InspectorName("Engeller")]
    [SerializeField] private Color obstacleColor = new Color(1, 0.24f, 0.47f);
    [InspectorName("Bitiş çizgisi")]
    [SerializeField] private Color finishColor = new Color(0.65f, 1, 0.3f);
    [Header("Zemin ışığı")]
    [SerializeField, Range(3, 14), InspectorName("Zemin ışığının genişliği")] private float spotlightRadius = 7.5f;
    [SerializeField, Range(0, 0.25f), InspectorName("Uzak zeminin görünürlüğü")] private float distantVisibility = 0.025f;
    [SerializeField, Range(0, 0.2f), InspectorName("Karenin parıltısı")] private float squareGlow = 0.025f;
    // Seçilen kaynak yalnız zıplama isteğinin nereden geleceğini belirler.
    private enum InputSource { Keyboard, Simulator, Radar }
    private InputSource source = InputSource.Keyboard;
    private readonly string[] sourceNames = { "Keyboard", "Simulation", "Experimental radar" };
    // Rigidbody2D hız ve yerçekimini, Collider2D yüzey temaslarını yönetir.
    private Rigidbody2D player;
    private Collider2D floor, playerCollider;
    private readonly List<Collider2D> obstacles = new List<Collider2D>();
    private const float FinishX = 28; // Karenin bu X konumuna ulaşması bölümü bitirir.
    private Camera gameCamera;
    private int worldCullingMask;
    private PrototypeCharacter character;
    private GameAccountClient account;
    private bool hadSession;
    private string roundInputSource = "keyboard";
    private Sprite sprite;
    private Sprite stageSurfaceSprite;
    private Texture2D stageSurfaceTexture;
    private int previousFrameTarget;
    private Material material, groundMaterial;
    private Socket socket;
    private readonly byte[] buffer = new byte[2049];
    // Her Python oturumu için son kabul edilen sıra numarası tutulur.
    private readonly Dictionary<string, long> sequences = new Dictionary<string, long>();
    private readonly LinkedList<string> sessions = new LinkedList<string>();
    private long selectedAt;
    private float horizontal;
    // jumpPending tek fizik adımında tüketilen istek, running turun devam durumudur.
    private bool jumpPending, running;
    private bool roundStarted;
    private float runStartsAt;
    // UDP paketleri, kabul edilen istekler ve gerçekleşen zıplamalar ayrı sayılır.
    private int requests, jumps, udpPackets;
    private string lastRejection = "—";
    private string result = "", connectionStatus = "Keyboard selected";

    // Python'ın JSON alanları aynı isimlerle bu C# nesnesine aktarılır.
    [Serializable]
    private class JumpMessage
    {
        public int schema_version;
        public string event_type, source, evidence, session_id;
        public bool experimental;
        public long sequence, sent_at_unix_ms;
    }

    // Bu sözleşme düz JSON'dur: sekiz bilinen alan ve yalnız basit değerler.
    // Alan kontrolü eksik alanların JsonUtility varsayılanlarıyla kabulünü önler.
    private static readonly Regex Field = new Regex(
        @"\G\s*""(?<key>[a-z_]+)""\s*:\s*(?<value>""[^""\\]*""|true|false|0|[1-9][0-9]*)\s*(?<end>,|})");
    private static readonly HashSet<string> FieldNames = new HashSet<string> {
        "schema_version", "event_type", "source", "evidence", "experimental",
        "session_id", "sequence", "sent_at_unix_ms"
    };

    // Unity, Play başladıktan sonra bu metodu bir kez çağırır.
    // Sahnedeki kamera, parkur ve kare burada oluşturulur.
    private void Start()
    {
        // PowerShell veya radar penceresi öndeyken de UDP istekleri zamanında işlenir.
        Application.runInBackground = true;
        previousFrameTarget = Application.targetFrameRate;
        Application.targetFrameRate = 120; // VSync açıksa ekranın yenileme hızı kullanılır.
        // Basit kutular dışarıdan görsel veya paket indirmeyi gerektirmez.
        sprite = Sprite.Create(Texture2D.whiteTexture,
            new Rect(0, 0, Texture2D.whiteTexture.width, Texture2D.whiteTexture.height),
            Vector2.one * 0.5f, Texture2D.whiteTexture.width);
        // Kare, engeller ve bitiş ortam ışığından bağımsız, kendi renklerinde çizilir.
        Shader shader = Shader.Find("Universal Render Pipeline/2D/Sprite-Unlit-Default");
        if (shader == null) shader = Shader.Find("Sprites/Default");
        if (shader != null) material = new Material(shader);
        // Merkezdeki ışık yalnız zemin panellerine ait ayrı malzemeye uygulanır.
        Shader groundShader = Resources.Load<Shader>("ScreenSpotlight2D");
        if (groundShader != null) groundMaterial = new Material(groundShader);
        Camera camera = Camera.main;
        if (camera == null)
        {
            camera = new GameObject("PrototypeCamera", typeof(Camera)).GetComponent<Camera>();
            camera.transform.SetParent(transform, false);
        }
        camera.orthographic = true; // 2D görünümde uzaktaki nesneler küçülmez.
        gameCamera = camera;
        worldCullingMask = camera.cullingMask;
        // Dar Game penceresinde başlangıç konumunun görünmesi için görüş alanını genişlet.
        camera.orthographicSize = Mathf.Max(6, 10 / Mathf.Max(camera.aspect, 0.01f));
        camera.transform.position = new Vector3(-6, 0, -10);
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = backgroundColor;
        floor = Box("Zemin", new Vector2(12, -2.25f), new Vector2(48, 0.5f),
            backgroundColor, true).GetComponent<Collider2D>();
        // Fizik yüzeyi aynı yerde kalır. Görünümü ayrı, hacimli platform panelleri çizer.
        floor.GetComponent<SpriteRenderer>().enabled = false;
        CreateStageSurface();
        // Parkurun engel konumları. Yeni bir X değeri eklemek yeni bir engel oluşturur.
        float[] obstaclePositions = { -1, 8, 17, 23 };
        foreach (float x in obstaclePositions)
        {
            GameObject block = Box("Engel", new Vector2(x, -1.6f), new Vector2(0.8f, 0.8f), Color.Lerp(backgroundColor, obstacleColor, 0.3f), true);
            obstacles.Add(block.GetComponent<Collider2D>());
            Box("Engel isigi", new Vector2(x, -1.225f), new Vector2(0.8f, 0.05f), Color.Lerp(obstacleColor, Color.white, 0.6f), false);
            Box("Engel yan kenari", new Vector2(x - 0.385f, -1.6f), new Vector2(0.03f, 0.8f), obstacleColor, false);
        }
        Box("Bitis", new Vector2(FinishX, -0.75f), new Vector2(0.15f, 2.5f),
            finishColor, false);
        GameObject actor = new GameObject("Karakter");
        actor.transform.SetParent(transform, false);
        actor.transform.position = new Vector2(-8, -1.6f);
        BoxCollider2D actorCollider = actor.AddComponent<BoxCollider2D>();
        actorCollider.size = new Vector2(0.8f, 0.8f); // Karenin fiziksel genişliği ve yüksekliği.
        playerCollider = actorCollider;
        player = actor.AddComponent<Rigidbody2D>();
        player.gravityScale = gravityScale; // Yerçekimini Unity'nin fizik sistemi uygular.
        player.freezeRotation = true; // Görsel dönebilir, çarpışma gövdesi dik kalır.
        // Sürekli çarpışma denetimi hızlı hareket sırasında engellerin atlanmasını azaltır.
        player.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
        player.interpolation = RigidbodyInterpolation2D.Interpolate; // Görüntüdeki hareketi yumuşatır.
        character = actor.AddComponent<PrototypeCharacter>();
        character.Initialize(player, playerCollider, floor, material, squareNeon, squareBody, squareGlow);
        account = gameObject.AddComponent<GameAccountClient>();
        account.Initialize(apiBaseUrl);
        gameObject.AddComponent<PrototypeInterface>().Initialize(this, account, squareNeon, backgroundColor);
        RestartRound();
    }

    // Ortak dikdörtgen oluşturucu. solid=true olduğunda nesneye fizik yüzeyi eklenir.
    private GameObject Box(string title, Vector2 position, Vector2 size, Color color, bool solid)
    {
        GameObject box = new GameObject(title);
        box.transform.SetParent(transform, false);
        box.transform.position = position;
        box.transform.localScale = new Vector3(size.x, size.y, 1);
        SpriteRenderer image = box.AddComponent<SpriteRenderer>();
        image.sprite = sprite;
        image.color = color;
        if (material != null) image.sharedMaterial = material;
        if (solid) box.AddComponent<BoxCollider2D>();
        return box;
    }

    // Tek, parlak çizgi yerine üst kenarı ve ön yüzeyi olan platform panelleri.
    // Çarpışma yüzeyi floor üzerindedir. Bu paneller yalnız görünümü oluşturur.
    private void CreateStageSurface()
    {
        const int width = 192, height = 64;
        Color[] pixels = new Color[width * height];
        Color face = Color.Lerp(backgroundColor, new Color(0.14f, 0.18f, 0.24f), 0.65f);
        Color edge = Color.Lerp(squareNeon, new Color(0.7f, 0.78f, 0.86f), 0.85f);
        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                Color color = Color.Lerp(face * 0.28f, face, y / 63f);
                if (y >= 59) color = Color.Lerp(face, edge, (y - 59) / 4f);
                if (x < 2 || x >= width - 2) color *= 0.28f;
                if ((x == 15 || x == width - 16) && y < 57) color *= 0.55f;
                color.a = 1;
                pixels[y * width + x] = color;
            }
        }
        stageSurfaceTexture = new Texture2D(width, height, TextureFormat.RGBA32, false);
        stageSurfaceTexture.name = "Platform yuzeyi";
        stageSurfaceTexture.filterMode = FilterMode.Bilinear;
        stageSurfaceTexture.wrapMode = TextureWrapMode.Clamp;
        stageSurfaceTexture.SetPixels(pixels);
        stageSurfaceTexture.Apply(false, true);
        stageSurfaceSprite = Sprite.Create(stageSurfaceTexture, new Rect(0, 0, width, height), Vector2.one * 0.5f, 64);
        for (int i = 0; i < 16; i++)
        {
            GameObject panel = new GameObject("Platform paneli");
            panel.transform.SetParent(transform, false);
            panel.transform.position = new Vector2(-10.5f + i * 3, -2.5f);
            SpriteRenderer image = panel.AddComponent<SpriteRenderer>();
            image.sprite = stageSurfaceSprite;
            image.sortingOrder = -2;
            image.sharedMaterial = groundMaterial != null ? groundMaterial : material;
        }
    }

    // Her görüntü karesinde tuşları ve UDP paketlerini kontrol eder.
    // Fiziksel hız değişiklikleri aşağıdaki FixedUpdate içinde uygulanır.
    private void Update()
    {
        // Giriş formuna yazılan Space/R harfleri oyun komutu olarak kullanılmaz.
        bool signedIn = account != null && account.IsAuthenticated;
        if (signedIn != hadSession) { hadSession = signedIn; RestartRound(); }
        if (!signedIn || account.IsBusy) { horizontal = 0; jumpPending = false; return; }
        bool space = false, restart = false;
        horizontal = 0;
#if ENABLE_INPUT_SYSTEM
        Keyboard keyboard = Keyboard.current;
        if (keyboard != null)
        {
            // Sağ yön +1, sol yön -1. İki yön birlikte basılırsa sonuç 0 olur.
            horizontal = (keyboard.dKey.isPressed || keyboard.rightArrowKey.isPressed ? 1 : 0)
                - (keyboard.aKey.isPressed || keyboard.leftArrowKey.isPressed ? 1 : 0);
            space = keyboard.spaceKey.wasPressedThisFrame;
            restart = keyboard.rKey.wasPressedThisFrame;
        }
#elif ENABLE_LEGACY_INPUT_MANAGER
        horizontal = (Input.GetKey(KeyCode.D) || Input.GetKey(KeyCode.RightArrow) ? 1 : 0)
            - (Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.LeftArrow) ? 1 : 0);
        space = Input.GetKeyDown(KeyCode.Space);
        restart = Input.GetKeyDown(KeyCode.R);
#endif
        if (restart) RestartRound();
        if (source == InputSource.Keyboard && space) jumpPending = true;
        ReceiveEvents();
    }

    // Unity fizik adımlarında çalışır. Kare hızı değişse de fizik düzenli adımlarla ilerler.
    private void FixedUpdate()
    {
        if (account == null || !account.IsAuthenticated || account.IsBusy) { jumpPending = false; return; }
        if (!running) { jumpPending = false; return; }
        if (!roundStarted || Time.time < runStartsAt) { jumpPending = false; return; }
        // Bir engele temas etmek, bitişi geçmek veya aşağı düşmek turu sonlandırır.
        foreach (Collider2D obstacle in obstacles)
        {
            if (playerCollider.IsTouching(obstacle)) { Finish("Obstacle hit. Press R to reset."); return; }
        }
        if (player.position.x >= FinishX) { Finish("Finish reached!"); return; }
        if (player.position.y < -5) { Finish("You fell. Press R to reset."); return; }
        Vector2 velocity = player.linearVelocity;
        // Yatay hız doğrudan hedef değere atanır. Kademeli yatay hızlanma uygulanmaz.
        // Otomatik modda +moveSpeed, manuel modda yön * moveSpeed kullanılır.
        velocity.x = autoRun ? moveSpeed : horizontal * moveSpeed;
        // İstek yalnız bu fizik adımında kullanılır; havada bekletilip inişte çalışmaz.
        // Zıplama için hem istek hem zemin teması gerekir. Havada ikinci kez zıplanmaz.
        if (jumpPending && playerCollider.IsTouching(floor) && velocity.y <= 0.05f)
        {
            velocity.y = jumpSpeed; // Zıplamanın ilk dikey hızı burada uygulanır.
            jumps++;
        }
        jumpPending = false;
        // Hız zaten birim/saniye cinsindedir. Burada deltaTime ile çarpılmaz.
        // Sonraki adımlarda yerçekimi dikey hızı azaltır, tepe noktasından sonra negatife çevirir.
        player.linearVelocity = velocity;
    }

    // Hareket hesaplandıktan sonra kamera kareyi biraz önden takip eder.
    private void LateUpdate()
    {
        if (player == null || gameCamera == null) return;
        Vector3 position = gameCamera.transform.position;
        // transform.position, Rigidbody2D'nin görüntü kareleri arasındaki yumuşatılmış konumudur.
        // Kamerayı doğrudan fizik adımlarına bağlamak görüntüde küçük sıçramalar oluşturabilir.
        float target = Mathf.Clamp(player.transform.position.x + 2, -6, FinishX - 2);
        position.x = Mathf.Lerp(position.x, target, 1 - Mathf.Exp(-8 * Time.deltaTime));
        gameCamera.transform.position = position;
        if (groundMaterial != null)
        {
            groundMaterial.SetVector("_SpotCenter", new Vector4(position.x, position.y, 0, 0));
            groundMaterial.SetVector("_SpotRadii", new Vector4(spotlightRadius, spotlightRadius * 0.75f, 0, 0));
            groundMaterial.SetFloat("_Ambient", distantVisibility);
        }
    }

    // Tur sonunda kareyi dondurur ve sonucu ekrana aktarır.
    private void Finish(string message)
    {
        running = false;
        result = message;
        player.linearVelocity = Vector2.zero;
        player.simulated = false;
        character.FinishPose(player.position.x >= FinishX);
        jumpPending = false;
        // Bitmiş tur bir kez kaydedilir. Skor şimdilik parkur ilerlemesi * 1000'dir.
        int duration = Mathf.RoundToInt(Mathf.Clamp((Time.time - runStartsAt) * 1000, 0, int.MaxValue));
        account.SaveRound(Score, duration, roundInputSource, player.position.x >= FinishX);
    }

    // Yeni denemede konumu, hızı, görsel izi ve tur sayaçlarını başlangıca döndürür.
    private void RestartRound()
    {
        if (player == null) return;
        player.simulated = account != null && account.IsAuthenticated;
        player.position = new Vector2(-8, -1.6f);
        player.linearVelocity = Vector2.zero;
        character.ResetPose();
        gameCamera.transform.position = new Vector3(-6, 0, -10);
        running = true;
        roundStarted = false;
        runStartsAt = Time.time;
        result = "";
        requests = jumps = 0;
        jumpPending = false;
        OpenReceiver();
    }

    // Seçili kaynak için yalnız bu bilgisayardaki 127.0.0.1 adresini dinler.
    private void OpenReceiver()
    {
        CloseReceiver();
        udpPackets = 0;
        lastRejection = "—";
        selectedAt = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        if (account != null && !account.IsAuthenticated) { connectionStatus = "Waiting for sign-in"; return; }
        if (source == InputSource.Keyboard) { connectionStatus = "Keyboard selected"; return; }
        try
        {
            socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
            socket.ExclusiveAddressUse = true;
            socket.Bind(new IPEndPoint(IPAddress.Loopback, udpPort));
            socket.Blocking = false;
            connectionStatus = "Waiting for Python events · 127.0.0.1:" + udpPort;
        }
        catch (Exception exc) when (exc is SocketException || exc is ArgumentOutOfRangeException)
        {
            CloseReceiver();
            connectionStatus = "Receiver unavailable. Close the other receiver using this port.";
        }
    }

    // Soket bekleyerek oyunu durdurmaz. Paketi doğrular ve fizik adımına istek bırakır.
    private void ReceiveEvents()
    {
        if (socket == null) return;
        // Her karede en fazla 32 mesaj; ağ kuyruğu oyun döngüsünü kilitlemez.
        for (int i = 0; i < 32; i++)
        {
            try
            {
                EndPoint sender = new IPEndPoint(IPAddress.Any, 0);
                int length = socket.ReceiveFrom(buffer, ref sender);
                udpPackets++;
                if (length == 0 || length > 2048)
                {
                    lastRejection = "Invalid packet size";
                    continue;
                }
                JumpMessage message = Validate(Encoding.UTF8.GetString(buffer, 0, length));
                if (message == null) continue;
                requests++;
                connectionStatus = "Event received · " + sourceNames[(int)source];
                if (running) jumpPending = true;
            }
            catch (SocketException exc)
            {
                if (exc.SocketErrorCode == SocketError.WouldBlock) break;
                if (exc.SocketErrorCode == SocketError.MessageSize)
                {
                    udpPackets++;
                    lastRejection = "Packet too large";
                    continue;
                }
                CloseReceiver();
                connectionStatus = "Receiver stopped: " + exc.SocketErrorCode;
                break;
            }
        }
    }

    // Alanları, kaynak bilgisini, zamanı ve olay sırasını kontrol eder.
    private JumpMessage Validate(string json)
    {
        if (!HasExpectedFields(json)) return Reject("Invalid JSON fields or types");
        JumpMessage message;
        try { message = JsonUtility.FromJson<JumpMessage>(json); }
        catch (ArgumentException) { return Reject("Invalid JSON"); }
        if (message == null || message.schema_version != 1 || message.event_type != "jump_request"
            || message.sequence < 1 || message.session_id == null
            || !Regex.IsMatch(message.session_id, "\\A[0-9a-f]{32}\\z")) return Reject("Invalid event, session or sequence");
        string wanted = source == InputSource.Simulator ? "simulator" : "radar";
        string evidence = source == InputSource.Simulator ? "simulated" : "motion_candidate";
        if (source == InputSource.Keyboard || message.source != wanted || message.evidence != evidence
            || message.experimental != (source == InputSource.Radar)) return Reject("Selected source mismatch");
        long now = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        // 1 saniyeden eski olaylar elenir. Gelecek zamana en fazla 250 ms tolerans vardır.
        if (message.sent_at_unix_ms <= now - 1000) return Reject("Packet older than 1 second");
        if (message.sent_at_unix_ms > now + 250) return Reject("Future packet timestamp");
        if (message.sent_at_unix_ms < selectedAt) return Reject("Packet sent before source selection");
        long previous;
        if (sequences.TryGetValue(message.session_id, out previous) && message.sequence <= previous) return Reject("Duplicate or old sequence");
        // Aynı oturumda geriye giden/yinelenen sıra numarası yeniden zıplatmaz.
        sequences[message.session_id] = message.sequence;
        sessions.Remove(message.session_id);
        sessions.AddLast(message.session_id);
        if (sessions.Count > 64)
        {
            sequences.Remove(sessions.First.Value);
            sessions.RemoveFirst();
        }
        return message;
    }

    // Ret nedenini Game ekranındaki tanı satırına bırakır.
    private JumpMessage Reject(string reason)
    {
        lastRejection = reason;
        return null;
    }

    // JSON'un beklenen sekiz alanı yalnız birer kez içerdiğini ve türlerini doğrular.
    private static bool HasExpectedFields(string json)
    {
        int index = 0;
        while (index < json.Length && char.IsWhiteSpace(json[index])) index++;
        if (index == json.Length || json[index++] != '{') return false;
        HashSet<string> seen = new HashSet<string>();
        while (index < json.Length)
        {
            Match match = Field.Match(json, index);
            if (!match.Success) return false;
            string key = match.Groups["key"].Value, value = match.Groups["value"].Value;
            if (!FieldNames.Contains(key) || !seen.Add(key)) return false;
            bool numeric = key == "schema_version" || key == "sequence" || key == "sent_at_unix_ms";
            if (key == "experimental") { if (value != "true" && value != "false") return false; }
            else if (numeric)
            {
                long number;
                if (!long.TryParse(value, out number)) return false;
                if (key == "schema_version" && number != 1) return false;
            }
            else if (value[0] != '"') return false;
            index = match.Index + match.Length;
            if (match.Groups["end"].Value == "}")
                return seen.Count == FieldNames.Count && string.IsNullOrWhiteSpace(json.Substring(index));
        }
        return false;
    }

    // PrototypeInterface yalnız bu okuma özelliklerini ve kontrollü metotları kullanır.
    public bool HasStarted => roundStarted;
    public bool IsRunning => running;
    public float Progress => player == null ? 0 : Mathf.Clamp01((player.position.x + 8) / (FinishX + 8));
    public int Score => Mathf.RoundToInt(Progress * 1000);
    public int JumpCount => jumps;
    public float Countdown => roundStarted ? Mathf.Max(0, runStartsAt - Time.time) : 0;
    public string ResultText => result;
    public int SourceSelection => (int)source;
    // Tam ekran menü resmi açıkken arkasında kalan parkur gereksiz yere çizilmez.
    public void SetWorldVisible(bool visible)
    {
        if (gameCamera != null) gameCamera.cullingMask = visible ? worldCullingMask : 0;
    }
    public string SourceLabel => source == InputSource.Radar ? "RADAR" : source == InputSource.Simulator ? "SIM" : "KEYBOARD";
    public string DiagnosticText => "Input / " + sourceNames[(int)source]
        + "\nRaw UDP " + udpPackets + " · Accepted " + requests + " · Jumps " + jumps
        + "\n" + connectionStatus + "\nLast rejection / " + lastRejection
        + "\nDisplay / approx. " + Mathf.RoundToInt(1 / Mathf.Max(Time.smoothDeltaTime, 0.001f)) + " FPS";

    public void SelectSource(int selection)
    {
        if (selection < 0 || selection >= sourceNames.Length || (running && roundStarted)) return;
        source = (InputSource)selection;
        jumpPending = false;
        OpenReceiver();
    }

    public void ReturnToLobby()
    {
        if (account == null || account.IsBusy) return;
        RestartRound();
    }

    public void RetryRun()
    {
        if (account == null || !account.IsAuthenticated || account.IsBusy) return;
        RestartRound();
        roundStarted = true;
        runStartsAt = Time.time + 3;
        roundInputSource = source == InputSource.Radar ? "radar" : source == InputSource.Simulator ? "simulator" : "keyboard";
    }

    // Bileşen kapatıldığında port serbest bırakılır, yeniden açılınca alıcı kurulur.
    private void OnEnable() { if (player != null) OpenReceiver(); }
    private void OnDisable() { jumpPending = false; CloseReceiver(); }
    private void CloseReceiver()
    {
        if (socket != null) { socket.Close(); socket = null; }
    }
    // Play biterken kodla üretilen kaynakları temizleyerek belleği serbest bırakır.
    private void OnDestroy()
    {
        CloseReceiver();
        if (sprite != null) Destroy(sprite);
        if (stageSurfaceSprite != null) Destroy(stageSurfaceSprite);
        if (stageSurfaceTexture != null) Destroy(stageSurfaceTexture);
        if (material != null) Destroy(material);
        if (groundMaterial != null) Destroy(groundMaterial);
        Application.targetFrameRate = previousFrameTarget;
    }
}
