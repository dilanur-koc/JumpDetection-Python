using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

// Görsel katman: arka plan, platform ışıkları, engel yüzeyi ve zıplama efektleri.
// Rigidbody hızını, zıplama sayısını veya kamera/radar kararlarını değiştirmez.
public sealed class NeonStage : MonoBehaviour
{
    private static readonly Color Cyan = new Color(0.15f, 0.95f, 1);
    private static readonly Color Pink = new Color(1, 0.25f, 0.7f);
    private static readonly Color Lime = new Color(0.7f, 1, 0.3f);
    private Sprite square;
    private Material sharedMaterial;
    private Camera view;
    private Rigidbody2D actor;
    private PrototypeCharacter character;
    private Transform city;
    private TrailRenderer trail;
    private ParticleSystem sparks;
    private Texture2D skyTexture;
    private Sprite skySprite;
    private Sprite citySprite;
    private SpriteRenderer cityBackdrop;
    private Texture2D hazardTexture;
    private Sprite hazardSprite;
    private VolumeProfile glowProfile;
    private bool wasGrounded = true;
    private int nextPulse;
    private readonly Pulse[] pulses = new Pulse[8];

    // Her zıplamada yeni nesne üretmek yerine sekiz halkayı sırayla yeniden kullanırız.
    // center dünya konumudur; kare ilerlese de halka kalkış noktasında kalır.
    private sealed class Pulse
    {
        public LineRenderer line;
        public LineRenderer halo;
        public readonly Vector3[] points = new Vector3[33];
        public Vector2 center;
        public Color color;
        public float started;
        public float strength;
        public float duration, radius;
    }

    public void Initialize(Sprite sprite, Material material, Camera camera, Rigidbody2D player,
        PrototypeCharacter playerCharacter, IReadOnlyList<Collider2D> platforms, IReadOnlyList<Collider2D> obstacles,
        float finishX)
    {
        square = sprite;
        sharedMaterial = material;
        view = camera;
        actor = player;
        character = playerCharacter;
        CreateSky();
        CreateCity();
        CreateCourseLights(platforms, obstacles, finishX);
        CreateEffects();
        CreateNeonGlow();
    }

    private SpriteRenderer Panel(string title, Transform parent, Vector2 position,
        Vector2 size, Color color, int order)
    {
        GameObject item = new GameObject(title);
        item.transform.SetParent(parent, false);
        item.transform.localPosition = position;
        item.transform.localScale = new Vector3(size.x, size.y, 1);
        SpriteRenderer image = item.AddComponent<SpriteRenderer>();
        image.sprite = square;
        image.sharedMaterial = sharedMaterial;
        image.color = color;
        image.sortingOrder = order;
        return image;
    }

    private LineRenderer Line(string title, Color color, float width, int order, params Vector3[] points)
    {
        GameObject item = new GameObject(title);
        item.transform.SetParent(transform, false);
        LineRenderer line = item.AddComponent<LineRenderer>();
        line.sharedMaterial = sharedMaterial;
        line.useWorldSpace = true;
        line.widthMultiplier = width;
        line.startColor = line.endColor = color;
        line.sortingOrder = order;
        line.numCornerVertices = 2;
        line.numCapVertices = 2;
        line.shadowCastingMode = ShadowCastingMode.Off;
        line.receiveShadows = false;
        line.positionCount = points.Length;
        line.SetPositions(points);
        return line;
    }

    private void CreateSky()
    {
        // Panoramanın arkasındaki sade mor geçiş, saydam resmi doldurur.
        // Texture2D'nin ikinci boyutu dikeydir; alt ve üst renk burada ayarlanır.
        const int height = 128;
        skyTexture = new Texture2D(1, height, TextureFormat.RGBA32, false);
        skyTexture.name = "Neon dusk";
        skyTexture.wrapMode = TextureWrapMode.Clamp;
        Color[] pixels = new Color[height];
        for (int y = 0; y < height; y++)
        {
            float t = y / (height - 1f);
            pixels[y] = Color.Lerp(new Color(0.16f, 0.055f, 0.26f),
                new Color(0.075f, 0.045f, 0.16f), t);
        }
        skyTexture.SetPixels(pixels);
        skyTexture.Apply(false, true);
        skySprite = Sprite.Create(skyTexture, new Rect(0, 0, 1, height), Vector2.one * 0.5f, 1);
        SpriteRenderer sky = Panel("Neon skyline sky", transform, new Vector2(14, 3),
            new Vector2(100, 24f / height), Color.white, -50);
        sky.sprite = skySprite;
    }

    private void CreateCity()
    {
        city = new GameObject("Distant neon city").transform;
        city.SetParent(transform, false);
        Texture2D panorama = Resources.Load<Texture2D>("NeonCityBackdrop");
        // Resources.Load yolunda uzantı kullanılmaz. Dosya Assets/Resources/NeonCityBackdrop.png'dir.
        // Sprite yalnız resmi çizer; şehir için Collider oluşturulmaz.
        if (panorama != null)
        {
            citySprite = Sprite.Create(panorama, new Rect(0, 0, panorama.width, panorama.height),
                Vector2.one * 0.5f, 100);
            cityBackdrop = Panel("Pixel neon panorama", city, new Vector2(6.5f, 0.25f),
                Vector2.one, new Color(1, 1, 1, 0.58f), -40);
            // Son renk bileşeni alfa: 0 tamamen saydam, 1 tamamen opak. Burada %58 opaktır.
            cityBackdrop.sprite = citySprite;
            FitPanorama();
            return;
        }

        // Görsel bulunamazsa şehir silüetiyle çalışmaya devam eder.
        var random = new System.Random(42);
        for (int i = 0; i < 23; i++)
        {
            float x = -18 + i * 3;
            float height = 2.2f + (float)random.NextDouble() * 4.2f;
            float width = 1.4f + (float)random.NextDouble() * 1.2f;
            Color accent = i % 3 == 0 ? Pink : Cyan;
            Panel("City tower", city, new Vector2(x, -2 + height * 0.5f),
                new Vector2(width, height), new Color(0.055f, 0.09f, 0.2f), -35);
            Panel("Tower neon edge", city, new Vector2(x - width * 0.5f, -2 + height * 0.5f),
                new Vector2(0.025f, height), new Color(accent.r, accent.g, accent.b, 0.3f), -34);
            for (int row = 0; row < Mathf.FloorToInt(height / 0.55f); row++)
                for (int column = 0; column < 3; column++)
                {
                    if (random.Next(3) == 0) continue;
                    Panel("Tower window", city, new Vector2(x - width * 0.28f + column * width * 0.28f,
                        -1.65f + row * 0.55f), new Vector2(width * 0.12f, 0.14f),
                        new Color(accent.r, accent.g, accent.b, 0.5f), -33);
                }
            Panel("Tower antenna", city, new Vector2(x, -2 + height + 0.35f),
                new Vector2(0.025f, 0.7f), new Color(accent.r, accent.g, accent.b, 0.5f), -34);
        }
    }

    private void FitPanorama()
    {
        if (cityBackdrop == null) return;
        // Geniş Game pencerelerinde de kenar açılmadan, oranı korunarak büyür.
        float height = Mathf.Max(12.5f, view.orthographicSize * 2 + 1);
        float width = view.orthographicSize * 2 * view.aspect + 18;
        float scale = Mathf.Max(height / citySprite.bounds.size.y, width / citySprite.bounds.size.x);
        cityBackdrop.transform.localScale = Vector3.one * scale;
    }

    private void CreateCourseLights(IReadOnlyList<Collider2D> platforms, IReadOnlyList<Collider2D> obstacles, float finishX)
    {
        // Çizgilerin sıralaması arkadan öne: şehir -40, zemin -2, ışıklar 0/1/2.
        // Zeminin üst kenarı kalır; altındaki kesik işaretler özellikle çizilmez.
        Line("Runway cyan edge", new Color(Cyan.r, Cyan.g, Cyan.b, 0.55f), 0.035f, 0,
            new Vector3(-12, -1.99f), new Vector3(finishX + 8, -1.99f));
        foreach (Collider2D platform in platforms) CreatePlatformLights(platform.bounds);
        CreateHazardArt(obstacles);
        Line("Finish portal", Lime, 0.07f, 2,
            new Vector3(finishX - 0.5f, -2), new Vector3(finishX - 0.5f, 0.8f),
            new Vector3(finishX + 0.5f, 0.8f), new Vector3(finishX + 0.5f, -2));
        Line("Finish portal halo", new Color(Lime.r, Lime.g, Lime.b, 0.16f), 0.25f, 1,
            new Vector3(finishX - 0.5f, -2), new Vector3(finishX - 0.5f, 0.8f),
            new Vector3(finishX + 0.5f, 0.8f), new Vector3(finishX + 0.5f, -2));
    }

    private void CreateHazardArt(IReadOnlyList<Collider2D> obstacles)
    {
        // Tek ortak doku tüm engellerde kullanılır. Collider'lar JumpPrototype'ta kalır.
        // Merkezde dolgu, kenarda pah/ışık, dışta saydam parıltı hesaplanır.
        const int size = 112;
        Color[] pixels = new Color[size * size];
        Color rim = new Color(1, 0.53f, 0.8f);
        for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                float dx = Mathf.Abs(x - 55.5f), dy = Mathf.Abs(y - 55.5f);
                // Pahlı köşeler ve tek parça, yumuşak renk geçişli yüzey; iç çizgi yoktur.
                float edge = Mathf.Max(Mathf.Max(dx, dy) - 39.5f, (dx + dy - 71) * 0.7071f);
                Color color;
                if (edge <= 0)
                {
                    float height = Mathf.Clamp01((y - 16) / 79f);
                    color = Color.Lerp(new Color(0.19f, 0.035f, 0.16f),
                        new Color(0.6f, 0.15f, 0.4f), height * height);
                    float bevel = 1 - Mathf.Clamp01((-edge - 2) / 6);
                    float light = y > 55 || x < 55 ? 0.48f : 0.17f;
                    color = Color.Lerp(color, rim, edge > -2 ? 0.95f : bevel * light);
                    color.a = 1;
                }
                else
                {
                    color = Pink;
                    color.a = Mathf.Exp(-edge * 0.32f) * 0.24f;
                }
                pixels[y * size + x] = color;
            }
        hazardTexture = new Texture2D(size, size, TextureFormat.RGBA32, false);
        hazardTexture.name = "Neon bevel hazard";
        hazardTexture.filterMode = FilterMode.Bilinear;
        hazardTexture.wrapMode = TextureWrapMode.Clamp;
        hazardTexture.SetPixels(pixels);
        hazardTexture.Apply(false, true);
        // 80 piksellik ana yüzey, mevcut 0.8 birimlik çarpışma alanıyla aynı boydadır.
        hazardSprite = Sprite.Create(hazardTexture, new Rect(0, 0, size, size), Vector2.one * 0.5f, 80);
        foreach (Collider2D obstacle in obstacles)
        {
            SpriteRenderer image = obstacle.GetComponent<SpriteRenderer>();
            image.sprite = hazardSprite;
            image.color = Color.white;
            image.sortingOrder = 2;
        }
    }

    private void CreatePlatformLights(Bounds deck)
    {
        // Ölçüleri collider sınırlarından alırız; platform yüksekliği değişince ışık ve ayakları da uyar.
        Line("Upper deck glow", Cyan, 0.06f, 2,
            new Vector3(deck.min.x, deck.max.y), new Vector3(deck.max.x, deck.max.y));
        Line("Upper deck glow halo", new Color(Cyan.r, Cyan.g, Cyan.b, 0.15f), 0.22f, 1,
            new Vector3(deck.min.x, deck.max.y), new Vector3(deck.max.x, deck.max.y));
        for (float x = deck.min.x + 0.4f; x < deck.max.x; x += 1.25f)
            Panel("Upper deck light", transform, new Vector2(x, deck.center.y),
                new Vector2(0.55f, 0.045f), Cyan, 2);
        for (float x = deck.min.x + 1; x < deck.max.x; x += 4)
        {
            float supportHeight = deck.min.y + 2;
            float supportY = -2 + supportHeight * 0.5f;
            Panel("Deck support", transform, new Vector2(x, supportY),
                new Vector2(0.12f, supportHeight), new Color(0.08f, 0.35f, 0.47f), -3);
            Panel("Deck support light", transform, new Vector2(x, supportY),
                new Vector2(0.035f, supportHeight - 0.1f), new Color(Cyan.r, Cyan.g, Cyan.b, 0.4f), -2);
        }
        // İki küçük ok, üst platforma yaklaşırken çıkış yönünü gösterir.
        for (int i = 0; i < 2 && deck.max.y >= -0.4f; i++)
        {
            float x = deck.min.x - 1.7f + i * 0.5f;
            Line("Upward route arrow", Lime, 0.045f, 1,
                new Vector3(x - 0.17f, deck.max.y - 0.9f), new Vector3(x, deck.max.y - 0.67f),
                new Vector3(x + 0.17f, deck.max.y - 0.9f));
        }
    }

    private void CreateEffects()
    {
        // TrailRenderer karenin arkasında kısa bir iz bırakır. time, izin saniye cinsinden ömrüdür.
        trail = actor.gameObject.AddComponent<TrailRenderer>();
        trail.sharedMaterial = sharedMaterial;
        trail.time = 0.16f;
        trail.minVertexDistance = 0.05f;
        trail.widthMultiplier = 0.16f;
        trail.startColor = new Color(Cyan.r, Cyan.g, Cyan.b, 0.6f);
        trail.endColor = new Color(Pink.r, Pink.g, Pink.b, 0);
        trail.sortingOrder = 1;
        trail.emitting = false;
        trail.shadowCastingMode = ShadowCastingMode.Off;

        GameObject particles = new GameObject("Neon sparks");
        // Otomatik parçacık yayılımı kapalıdır; yalnız EmitJump/iniş/bitiş çağrıları parçacık üretir.
        // World simülasyonu kıvılcımların kareye yapışmadan kalkış yerinden dağılmasını sağlar.
        particles.transform.SetParent(transform, false);
        sparks = particles.AddComponent<ParticleSystem>();
        sparks.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        var main = sparks.main;
        main.playOnAwake = false;
        main.loop = true;
        main.startLifetime = new ParticleSystem.MinMaxCurve(0.18f, 0.28f);
        main.startSize = new ParticleSystem.MinMaxCurve(0.035f, 0.065f);
        main.startSpeed = 0;
        main.gravityModifier = 0.25f;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.maxParticles = 96;
        var emission = sparks.emission;
        emission.enabled = false;
        var shape = sparks.shape;
        shape.enabled = false;
        var fade = sparks.colorOverLifetime;
        fade.enabled = true;
        Gradient fading = new Gradient();
        fading.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
            new[] { new GradientAlphaKey(0.8f, 0), new GradientAlphaKey(0, 1) });
        fade.color = fading;
        // Parçacık ömrü boyunca alfa 0'a, boyut dörtte bire iner; aniden kaybolmaz.
        var size = sparks.sizeOverLifetime;
        size.enabled = true;
        size.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, 1, 1, 0.25f));
        ParticleSystemRenderer renderer = particles.GetComponent<ParticleSystemRenderer>();
        renderer.sharedMaterial = sharedMaterial;
        renderer.sortingOrder = 5;
        sparks.Play();
        for (int i = 0; i < pulses.Length; i++)
        {
            LineRenderer line = Line("Jump pulse", Cyan, 0.035f, 4, new Vector3[33]);
            line.enabled = false;
            LineRenderer halo = Line("Jump pulse halo", Cyan, 0.18f, 3, new Vector3[33]);
            halo.enabled = false;
            pulses[i] = new Pulse { line = line, halo = halo };
        }
    }

    private void CreateNeonGlow()
    {
        // Bloom yalnız parlak piksellerin çevresine yumuşak ışık yayar; ekranı aydınlatan fiziksel ışık değildir.
        view.allowHDR = true;
        view.GetUniversalAdditionalCameraData().renderPostProcessing = true;
        GameObject lighting = new GameObject("Neon glow");
        lighting.transform.SetParent(transform, false);
        Volume volume = lighting.AddComponent<Volume>();
        volume.isGlobal = true;
        glowProfile = ScriptableObject.CreateInstance<VolumeProfile>();
        Bloom bloom = glowProfile.Add<Bloom>(true);
        bloom.threshold.Override(0.6f);
        bloom.intensity.Override(0.7f);
        bloom.scatter.Override(0.6f);
        volume.sharedProfile = glowProfile;
    }

    public void EmitJump(Vector2 position)
    {
        // position karenin merkezidir. 0.38 aşağısı ayak hizasıdır (kare yüksekliği 0.8).
        // Kıvılcım sayısı 12; gerçek boyut, hız ve ömür EmitBurst içindeki jump dalında ayarlanır.
        EmitBurst(position - Vector2.up * 0.38f, new Color(0.3f, 1.25f, 1.5f), 12, 1, true);
    }

    public void EmitFinish(Vector2 position)
    {
        EmitBurst(position, Lime, 24);
    }

    private void EmitBurst(Vector2 position, Color color, int amount, float strength = 1, bool jump = false)
    {
        // Zıplama daha belirgin, iniş daha küçük ve kısadır. Halkayı ve kıvılcımları aynı noktada başlat.
        Pulse pulse = pulses[nextPulse];
        nextPulse = (nextPulse + 1) % pulses.Length;
        pulse.center = position;
        pulse.color = color;
        pulse.started = Time.time;
        pulse.strength = strength;
        pulse.duration = jump ? 0.45f : 0.3f;
        pulse.radius = jump ? 1.1f : 0.75f;
        pulse.line.widthMultiplier = jump ? 0.06f : 0.035f;
        pulse.line.enabled = true;
        pulse.halo.enabled = jump;
        for (int i = 0; i < amount; i++)
            sparks.Emit(new ParticleSystem.EmitParams {
                position = position + new Vector2(Random.Range(-0.16f, 0.16f), 0),
                velocity = new Vector3(Random.Range(-2.1f, 2.1f),
                    jump ? Random.Range(1.6f, 3.2f) : Random.Range(0.5f, 2.1f)) * strength,
                startColor = color,
                startSize = jump ? Random.Range(0.075f, 0.12f) : Random.Range(0.035f, 0.065f),
                startLifetime = jump ? Random.Range(0.32f, 0.46f) : Random.Range(0.18f, 0.28f),
            }, 1);
    }

    public void ResetEffects()
    {
        // RETRY sırasında önceki turdan iz, parçacık veya açık halka bırakma.
        if (trail != null) trail.Clear();
        if (sparks != null) sparks.Clear();
        foreach (Pulse pulse in pulses)
            if (pulse != null) { pulse.line.enabled = false; pulse.halo.enabled = false; }
        wasGrounded = true;
    }

    private void LateUpdate()
    {
        if (actor == null) return;
        city.localPosition = new Vector3(view.transform.position.x * 0.65f, 0, 0);
        // Kamera ile aynı miktarda kaymadığı için şehir daha yavaş akar (paralaks derinliği).
        FitPanorama();
        bool grounded = character.IsGrounded;
        trail.emitting = actor.simulated && Mathf.Abs(actor.linearVelocity.x) > 0.2f;
        if (actor.simulated && grounded && !wasGrounded)
            EmitBurst(actor.position - Vector2.up * 0.38f, Pink, 4, 0.5f);
        wasGrounded = grounded;
        foreach (Pulse pulse in pulses)
        {
            if (!pulse.line.enabled) continue;
            float age = (Time.time - pulse.started) / pulse.duration;
            // age 0→1 iken halka genişler ve solar. Tamamlanınca havuza geri döner.
            if (age >= 1)
            {
                pulse.line.enabled = false;
                pulse.halo.enabled = false;
                continue;
            }
            Color color = pulse.color;
            color.a = (1 - age) * 0.9f;
            pulse.line.startColor = pulse.line.endColor = color;
            color.a = (1 - age) * 0.18f;
            pulse.halo.startColor = pulse.halo.endColor = color;
            float radius = Mathf.Lerp(0.12f, pulse.radius, age) * pulse.strength;
            for (int i = 0; i < pulse.points.Length; i++)
            {
                float angle = i * Mathf.PI * 2 / (pulse.points.Length - 1);
                pulse.points[i] = new Vector3(pulse.center.x + Mathf.Cos(angle) * radius,
                    pulse.center.y + Mathf.Sin(angle) * radius * 0.22f);
            }
            pulse.line.SetPositions(pulse.points);
            if (pulse.halo.enabled) pulse.halo.SetPositions(pulse.points);
        }
    }

    private void OnDestroy()
    {
        // Çalışma anında üretilen dokuları/sprite'ları temizle. Resources'taki PNG'yi silme.
        if (skySprite != null) Destroy(skySprite);
        if (citySprite != null) Destroy(citySprite);
        if (skyTexture != null) Destroy(skyTexture);
        if (hazardSprite != null) Destroy(hazardSprite);
        if (hazardTexture != null) Destroy(hazardTexture);
        if (glowProfile != null) Destroy(glowProfile);
    }
}
