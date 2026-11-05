using UnityEngine;

// Animasyon yalnız görsel çocuğu döndürür. Fizik gövdesi dik kalır.
public sealed class PrototypeCharacter : MonoBehaviour
{
    // body gerçek fizik gövdesidir. visual onun altında çizilen neon karedir.
    // Görseli döndürmek, zemine veya engele temas eden Collider2D'yi döndürmez.
    private Rigidbody2D body;
    private Collider2D actorCollider, ground;
    private Transform visual;
    private SpriteRenderer image;
    private Sprite squareSprite;
    private Texture2D squareTexture;
    private float angle; // Görsel dönüş açısı, derece cinsinden tutulur.
    private bool finished, won;

    // JumpPrototype fizik gövdesini, zemini ve Inspector'daki renkleri bu metoda verir.
    public void Initialize(Rigidbody2D actor, Collider2D collider, Collider2D floor,
        Material material, Color neon, Color shell, float glowStrength)
    {
        body = actor;
        actorCollider = collider;
        ground = floor;
        visual = new GameObject("Neon kare").transform;
        visual.SetParent(transform, false);
        image = visual.gameObject.AddComponent<SpriteRenderer>();
        image.sortingOrder = 2; // Zeminden ve ışık izinden önde çizilir.
        if (material != null) image.sharedMaterial = material;
        squareTexture = DrawSquare(neon, shell, glowStrength);
        // 80 piksel = 1 dünya birimi. Kare dolgusu 64 piksel, yani 0.8 birim genişliktedir.
        // Dışarıdaki saydam pikseller parıltı için ayrılmıştır.
        squareSprite = Sprite.Create(squareTexture, new Rect(0, 0, 112, 112), Vector2.one * 0.5f, 80);
        image.sprite = squareSprite;

        ResetPose();
    }

    // Yeni turda görsel dönüşü, rengi ve ölçeği sıfırlar.
    public void ResetPose()
    {
        finished = won = false;
        angle = 0;
        visual.localRotation = Quaternion.identity;
        visual.localScale = Vector3.one;
        image.color = Color.white;
    }

    // Tur bittiğinde başarı veya kayıp görünümüne geçmek için çağrılır.
    public void FinishPose(bool success)
    {
        finished = true;
        won = success;
    }

    // Fizik hareketinden sonra yalnız görünümü günceller.
    private void LateUpdate()
    {
        if (body == null) return;
        Vector2 velocity = body.linearVelocity;
        bool airborne = body.simulated && !actorCollider.IsTouching(ground); // Zemin teması yoksa havadadır.
        if (finished)
        {
            float pulse = 1 + Mathf.Sin(Time.time * 5) * 0.035f; // Tur sonunda hafif büyüyüp küçülme.
            visual.localScale = Vector3.one * pulse;
            image.color = won ? Color.white : new Color(1, 0.45f, 0.65f);
        }
        else
        {
            // Havada saniyede 300 derece döner. deltaTime, dönüşü kare hızından bağımsız kılar.
            if (airborne) angle -= 300 * Time.deltaTime;
            // Yere inince en yakın 90 derecelik açıya oturur.
            else angle = Mathf.MoveTowardsAngle(angle, Mathf.Round(angle / 90) * 90, 700 * Time.deltaTime);
            visual.localRotation = Quaternion.Euler(0, 0, angle);
            visual.localScale = Vector3.one;
        }
    }

    // Kare resmi dosyadan yüklenmez, renkli piksellerle burada üretilir.
    // neon kenar/parıltı rengidir. shell sade iç dolgu rengidir.
    private static Texture2D DrawSquare(Color neon, Color shell, float glowStrength)
    {
        const int size = 112;
        Color[] pixels = new Color[size * size];
        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                float dx = Mathf.Abs(x - 55.5f), dy = Mathf.Abs(y - 55.5f);
                float edge = Mathf.Max(dx, dy); // Merkezden en uzak eksen, kare sınırını tanımlar.
                Color color;
                if (edge > 32)
                {
                    float distance = edge - 32;
                    float glow = Mathf.Exp(-distance * distance / 35) * glowStrength;
                    float shadowDistance = Mathf.Max(0, Mathf.Max(Mathf.Abs(x - 59.5f), Mathf.Abs(y - 51.5f)) - 32);
                    float shadow = Mathf.Exp(-shadowDistance * shadowDistance / 32) * 0.12f;
                    float alpha = glow + shadow * (1 - glow);
                    color = neon * (glow / Mathf.Max(alpha, 0.001f));
                    color.a = alpha;
                }
                else
                {
                    color = Color.Lerp(shell, Color.white, y / 111f * 0.06f); // Hafif ışık alan mat yüzey.
                    if (edge > 26.5f) color = Color.Lerp(shell, Color.black, 0.25f); // İçte ince gölge.
                    if (edge > 28) color = Color.Lerp(neon, Color.white, 0.2f); // Dört piksel kalınlığında kenar.
                    if (edge > 31) color = Color.Lerp(neon, Color.white, 0.4f); // Hafif dış yüzey ışığı.
                }
                pixels[y * size + x] = color;
            }
        }
        Texture2D texture = new Texture2D(size, size, TextureFormat.RGBA32, false);
        texture.name = "CyberpunkSquare";
        texture.filterMode = FilterMode.Bilinear; // Pikseller arasındaki geçişi yumuşatır.
        texture.wrapMode = TextureWrapMode.Clamp;
        texture.SetPixels(pixels);
        texture.Apply(false, true);
        return texture;
    }

    // Play kapandığında bu sınıfın oluşturduğu resim ve malzemeleri bellekten kaldırır.
    private void OnDestroy()
    {
        if (squareSprite != null) Destroy(squareSprite);
        if (squareTexture != null) Destroy(squareTexture);
    }
}
