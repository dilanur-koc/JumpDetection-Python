using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Aynı ilk sahne, Editor menüsünden veya komut satırından tekrar oluşturulabilir.
public static class PrototypeSceneSetup
{
    // Bu sınıf yalnız Unity Editor'de çalışır. Oyunun Radar menüsündeki komutunu oluşturur.
    [MenuItem("Radar/Oyun sahnesini ac veya olustur")]
    public static void CreateScene()
    {
        // Menüden çalıştırıldığında açık sahnedeki düzenlemeler için kayıt sorulsun.
        if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
        {
            return;
        }

        const string scenePath = "Assets/Scenes/Prototype.unity";
        if (File.Exists(scenePath))
        {
            // Daha önce kaydedilmiş sahne varsa kullanıcı ayarlarıyla birlikte açılır.
            EditorSceneManager.OpenScene(scenePath);
            return;
        }

        // İlk kurulumda boş sahne ve oyun yöneticisi oluşturulur.
        // Zemin, engeller ve kare, JumpPrototype.Start tarafından Play sırasında üretilir.
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var prototype = new GameObject("Prototype");
        prototype.AddComponent<JumpPrototype>();

        Directory.CreateDirectory("Assets/Scenes");
        if (!EditorSceneManager.SaveScene(scene, scenePath))
        {
            throw new IOException("Ilk oyun sahnesi kaydedilemedi.");
        }

        // Sahne, Windows oyun çıktısına dahil edilecek sahneler listesine eklenir.
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(scenePath, true) };
        AssetDatabase.SaveAssets();
        Selection.activeGameObject = prototype;
        Debug.Log("Prototype scene ready at " + scenePath);
    }
}
