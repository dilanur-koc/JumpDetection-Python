using System;
using System.Globalization;
using UnityEngine;

// Ekranların yerleşimi burada. Hesap işlemleri GameAccountClient, fizik JumpPrototype içindedir.
public sealed class PrototypeInterface : MonoBehaviour
{
    private enum Page { Home, Account, Levels, Settings, Controls, Run }
    private Page page = Page.Home;
    private JumpPrototype game;
    private GameAccountClient account;
    private Color accent, background;
    private Texture2D backdrop;
    private string userName = "", password = "";
    private bool registering, history, diagnostics, hadSession, showFps;
    private GUIStyle label, small, caption, heading, brand, menu, button, field, number;
    private readonly string[] inputNames = { "KEYBOARD", "SIMULATION", "RADAR" };

    // Play sırasında kod yenilenirse eski ekrandan kalan GUIStyle nesneleri tekrar kullanılmaz.
    private void OnEnable()
    {
        label = null;
        backdrop = Resources.Load<Texture2D>("MenuBackdrop");
    }

    public void Initialize(JumpPrototype owner, GameAccountClient client, Color neon, Color backdropColor)
    {
        game = owner; account = client; accent = neon; background = backdropColor;
        // Tek sabit resim bir kez yüklenir. Küp animasyonu, paralaks ve piksel üretimi yoktur.
        backdrop = Resources.Load<Texture2D>("MenuBackdrop");
        showFps = PlayerPrefs.GetInt("NeonLink.ShowFPS", 0) == 1;
    }

    private void Update()
    {
        if (account == null) return;
        bool signedIn = account.IsAuthenticated;
        if (signedIn != hadSession)
        {
            hadSession = signedIn;
            password = "";
            page = signedIn ? Page.Levels : Page.Home;
        }
        // R ile tur sıfırlandığında bölüm seçimine dönülür.
        if (page == Page.Run && !game.HasStarted) page = Page.Levels;
        game.SetWorldVisible(page == Page.Run && signedIn);
    }

    private void OnGUI()
    {
        if (game == null || account == null) return;
        if (label == null || caption == null || menu == null || field == null) CreateStyles();
        // Aynı yerleşim farklı çözünürlüklerde korunur. Görselin en-boy oranı bozulmaz.
        float scale = Mathf.Max(0.1f, Mathf.Min(Screen.width / 1280f, Screen.height / 720f));
        Matrix4x4 previous = GUI.matrix;
        Color previousColor = GUI.color;
        bool previousEnabled = GUI.enabled;
        GUI.matrix = Matrix4x4.Scale(Vector3.one * scale);
        float width = Screen.width / scale, height = Screen.height / scale;
        try
        {
            if (page == Page.Run && account.IsAuthenticated)
            {
                DrawHud(width, height);
                if (!game.IsRunning) DrawResult(width, height);
                else if (game.Countdown > 0)
                    GUI.Label(new Rect(width / 2 - 90, height / 2 - 80, 180, 150),
                        Mathf.CeilToInt(game.Countdown).ToString(), number);
                if (diagnostics) DrawDiagnostics(width, height);
            }
            else
            {
                DrawBackdrop(width, height);
                float left = Mathf.Max(76, (width - 1128) / 2);
                switch (page)
                {
                    case Page.Account: DrawAccount(left, height); break;
                    case Page.Levels: DrawLevels(left, width, height); break;
                    case Page.Settings: DrawSettings(left, height); break;
                    case Page.Controls: DrawControls(left, height); break;
                    default: DrawHome(left, height); break;
                }
                GUI.Label(new Rect(left, height - 42, 600, 22), "NEON / LINK     •     RADAR PLATFORM PROTOTYPE", caption);
            }
            if (showFps)
                GUI.Label(new Rect(width - 100, height - 36, 84, 22),
                    Mathf.RoundToInt(1 / Mathf.Max(Time.smoothDeltaTime, 0.001f)) + " FPS", caption);
        }
        finally { GUI.matrix = previous; GUI.color = previousColor; GUI.enabled = previousEnabled; }
    }

    private void DrawBackdrop(float width, float height)
    {
        Fill(new Rect(0, 0, width, height), background);
        if (backdrop != null) GUI.DrawTexture(new Rect(0, 0, width, height), backdrop, ScaleMode.ScaleAndCrop);
    }

    private void DrawHome(float left, float height)
    {
        float top = Mathf.Max(106, (height - 500) / 2);
        GUI.Label(new Rect(left + 3, top, 450, 24), "MOVE WITH THE SIGNAL", caption);
        GUI.Label(new Rect(left, top + 34, 580, 88), "NEON / LINK", brand);
        Fill(new Rect(left + 3, top + 140, 48, 2), accent);
        GUI.Label(new Rect(left + 3, top + 164, 410, 62), "Find your rhythm.\nMake the jump.", label);
        if (MenuButton(new Rect(left, top + 258, 350, 50), "PLAY"))
            page = account.IsAuthenticated ? Page.Levels : Page.Account;
        if (MenuButton(new Rect(left, top + 316, 350, 46), "SETTINGS")) page = Page.Settings;
        if (MenuButton(new Rect(left, top + 370, 350, 46), "HOW TO PLAY")) page = Page.Controls;
        if (MenuButton(new Rect(left, top + 424, 350, 46), "QUIT")) Quit();
    }

    // Kalın kart/gölge yerine resmin üstünde sade, saydam form.
    private void DrawAccount(float left, float height)
    {
        float top = Mathf.Max(95, (height - 510) / 2);
        if (TextButton(new Rect(left, top - 45, 110, 30), "‹  BACK")) { password = ""; page = Page.Home; }
        GUI.Label(new Rect(left, top, 450, 30), "NEON / LINK", caption);
        GUI.Label(new Rect(left - 2, top + 38, 450, 56), registering ? "CREATE ACCOUNT" : "SIGN IN", heading);
        GUI.Label(new Rect(left, top + 108, 400, 30), registering ? "Your next run starts here." : "Continue your run.", small);
        GUI.enabled = !account.IsBusy;
        userName = Input(new Rect(left, top + 172, 380, 52), "USERNAME", "username", userName, false, 32);
        password = Input(new Rect(left, top + 278, 380, 52), "PASSWORD", "password", password, true, 128);
        GUI.Label(new Rect(left, top + 344, 380, 28), "8–128 characters", caption);
        if (ActionButton(new Rect(left, top + 394, 380, 48), account.IsBusy ? "CONNECTING…" : registering ? "CREATE ACCOUNT" : "SIGN IN"))
            account.Authenticate(userName, password, registering);
        if (TextButton(new Rect(left, top + 454, 380, 32), registering ? "Already have an account?  Sign in" : "New here?  Create an account"))
            registering = !registering;
        GUI.enabled = true;
        GUI.Label(new Rect(left, top + 500, 430, 60), account.Message, small);
        if (!account.IsBusy && Event.current.type == EventType.KeyDown && Event.current.keyCode == KeyCode.Return
            && (GUI.GetNameOfFocusedControl() == "username" || GUI.GetNameOfFocusedControl() == "password"))
        {
            account.Authenticate(userName, password, registering);
            Event.current.Use();
        }
    }

    private string Input(Rect rect, string text, string control, string value, bool secret, int length)
    {
        GUI.Label(new Rect(rect.x, rect.y - 28, rect.width, 22), text, caption);
        bool hover = rect.Contains(Event.current.mousePosition);
        // Tüm GUIStyle durumları aynı: Unity'nin varsayılan kabartma/hover dokuları kullanılmaz.
        Fill(rect, new Color(0.04f, 0.08f, 0.12f, hover ? 0.28f : 0.17f));
        Fill(new Rect(rect.x, rect.yMax - 1, rect.width, 1), new Color(0.65f, 0.87f, 0.94f, hover ? 0.55f : 0.25f));
        GUI.SetNextControlName(control);
        return secret ? GUI.PasswordField(rect, value, '•', length, field) : GUI.TextField(rect, value, length, field);
    }

    private void DrawLevels(float left, float width, float height)
    {
        float top = Mathf.Max(100, (height - 490) / 2);
        GUI.enabled = !account.IsBusy;
        if (TextButton(new Rect(left, top - 48, 120, 30), "‹  HOME")) page = Page.Home;
        if (TextButton(new Rect(width - left - 120, top - 48, 120, 30), "SIGN OUT")) account.Logout();
        GUI.enabled = true;
        GUI.Label(new Rect(left, top, 650, 54), history ? "RECENT RUNS" : "SELECT A RUN", heading);
        GUI.Label(new Rect(left, top + 68, 600, 30), account.User.userName + "  /  " + (history ? "Your latest five results." : "One signal. One jump at a time."), small);
        GUI.enabled = !account.IsBusy;
        if (history) DrawHistory(left, top + 140);
        else
        {
            // Sonraki bölümler henüz yapılmadı: seçilemez ve API'ye sonuç gönderemezler.
            for (int i = 0; i < 5; i++)
            {
                Rect card = new Rect(left + i * 176, top + 138, 160, 170);
                bool available = i == 0;
                Fill(card, new Color(0.02f, 0.05f, 0.08f, available ? 0.5f : 0.28f));
                Fill(new Rect(card.x, card.y, card.width, available ? 2 : 1), available ? accent : new Color(0.6f, 0.75f, 0.85f, 0.16f));
                GUI.Label(new Rect(card.x + 16, card.y + 14, 120, 58), (i + 1).ToString("00"), heading);
                GUI.Label(new Rect(card.x + 16, card.y + 93, 132, 45), available ? "FIRST CONTACT" : "COMING SOON", caption);
                GUI.Label(new Rect(card.x + 16, card.y + 138, 132, 20), available ? "READY TO PLAY" : "IN DEVELOPMENT", caption);
            }
            int selection = GUI.Toolbar(new Rect(left, top + 340, 500, 40), game.SourceSelection, inputNames, button);
            if (selection != game.SourceSelection) game.SelectSource(selection);
            GUI.Label(new Rect(left, top + 392, 850, 38), SourceHint(), small);
            if (ActionButton(new Rect(left, top + 445, 250, 46), "START RUN")) { game.RetryRun(); page = Page.Run; }
        }
        if (TextButton(new Rect(left + 290, top + 452, 170, 32), history ? "SELECT A RUN" : "RECENT RUNS")) history = !history;
        if (history && TextButton(new Rect(left + 490, top + 452, 120, 32), "REFRESH")) account.Refresh();
        GUI.enabled = true;
        GUI.Label(new Rect(left, top + 510, 880, 42), account.Message, small);
    }

    private string SourceHint()
    {
        return game.SourceSelection == 2 ? "Wait for the radar window to be ready, then start. Radar detection is experimental."
            : game.SourceSelection == 1 ? "Start the run, wait for the countdown, then send jump events from the Python simulator."
            : "Automatic movement. Press SPACE to jump. Press R to return to run selection.";
    }

    // HUD tamamen saydamdır. İlerleme çizgisi, yüzdelik gösterge ve geniş üst kart yoktur.
    private void DrawHud(float width, float height)
    {
        GUI.Label(new Rect(36, 28, 270, 26), "01  /  FIRST CONTACT", caption);
        GUI.Label(new Rect(36, 56, 270, 24), account.User.userName, small);
        GUI.enabled = !account.IsBusy;
        if (TextButton(new Rect(width - 225, 26, 90, 30), "MENU")) { game.ReturnToLobby(); page = Page.Levels; }
        GUI.enabled = true;
        if (TextButton(new Rect(width - 122, 26, 90, 30), "DEBUG")) diagnostics = !diagnostics;
        GUI.Label(new Rect(36, height - 42, 350, 22), game.SourceLabel, caption);
    }

    private void DrawResult(float width, float height)
    {
        float left = (width - 530) / 2, top = (height - 240) / 2;
        Fill(new Rect(left - 28, top - 22, 586, 280), new Color(0.015f, 0.025f, 0.055f, 0.72f));
        GUI.Label(new Rect(left, top, 530, 50), game.Progress >= 1 ? "RUN COMPLETE" : "TRY AGAIN", heading);
        GUI.Label(new Rect(left, top + 66, 530, 30), "SCORE  " + game.Score + "     /     JUMPS  " + game.JumpCount, small);
        GUI.Label(new Rect(left, top + 108, 530, 36), account.Message, small);
        GUI.enabled = !account.IsBusy;
        if (ActionButton(new Rect(left, top + 174, 245, 44), "RETRY")) game.RetryRun();
        if (TextButton(new Rect(left + 275, top + 180, 245, 32), "SELECT A RUN")) { game.ReturnToLobby(); page = Page.Levels; }
        GUI.enabled = true;
    }

    private void DrawHistory(float left, float top)
    {
        GUI.Label(new Rect(left, top, 840, 24), "DATE                              SCORE                  TIME                   RESULT", caption);
        if (account.Results.Length == 0) GUI.Label(new Rect(left, top + 45, 800, 30), "No runs yet. Your first result will appear here.", small);
        for (int i = 0; i < account.Results.Length && i < 5; i++)
        {
            var result = account.Results[i];
            DateTime date;
            string stamp = DateTime.TryParse(result.createdAtUtc, CultureInfo.InvariantCulture,
                DateTimeStyles.RoundtripKind, out date) ? date.ToLocalTime().ToString("dd MMM  HH:mm", CultureInfo.InvariantCulture) : "—";
            float y = top + 42 + i * 34;
            GUI.Label(new Rect(left, y, 220, 28), stamp, small);
            GUI.Label(new Rect(left + 240, y, 130, 28), result.score.ToString(), small);
            GUI.Label(new Rect(left + 420, y, 130, 28), (result.durationMs / 1000f).ToString("0.0", CultureInfo.InvariantCulture) + " s", small);
            GUI.Label(new Rect(left + 600, y, 220, 28), result.completed ? "COMPLETE" : "NOT COMPLETED", small);
        }
    }

    private void DrawSettings(float left, float height)
    {
        float top = (height - 400) / 2;
        if (TextButton(new Rect(left, top - 60, 120, 32), "‹  HOME")) page = Page.Home;
        GUI.Label(new Rect(left, top, 500, 60), "SETTINGS", heading);
        GUI.Label(new Rect(left, top + 92, 400, 32), "Frame rate display", label);
        if (TextButton(new Rect(left + 280, top + 92, 110, 32), showFps ? "ON" : "OFF"))
        {
            showFps = !showFps;
            PlayerPrefs.SetInt("NeonLink.ShowFPS", showFps ? 1 : 0);
            PlayerPrefs.Save();
        }
        GUI.Label(new Rect(left, top + 165, 420, 85), "Audio is not available in this prototype.\nMusic and volume controls will arrive with the soundtrack.", small);
    }

    private void DrawControls(float left, float height)
    {
        float top = (height - 450) / 2;
        if (TextButton(new Rect(left, top - 50, 120, 32), "‹  HOME")) page = Page.Home;
        GUI.Label(new Rect(left, top, 520, 60), "HOW TO PLAY", heading);
        GUI.Label(new Rect(left, top + 95, 450, 330),
            "Keep moving. Jump at the right moment.\n\nKEYBOARD\nSPACE to jump. R to reset.\n\nRADAR\nConnect the sensor and run the Python radar bridge. Detection is experimental.\n\nSIMULATION\nSend jump events from the Python simulator.", small);
    }

    private void DrawDiagnostics(float width, float height)
    {
        Fill(new Rect(width - 440, height - 210, 408, 150), new Color(0.01f, 0.02f, 0.04f, 0.72f));
        GUI.Label(new Rect(width - 424, height - 196, 376, 125), game.DiagnosticText, small);
    }

    private bool MenuButton(Rect rect, string text)
    {
        bool hover = GUI.enabled && rect.Contains(Event.current.mousePosition);
        if (hover) Fill(new Rect(rect.x - 18, rect.y + 14, 3, 22), accent);
        return GUI.Button(rect, text, menu);
    }

    private bool TextButton(Rect rect, string text)
    {
        if (GUI.enabled && rect.Contains(Event.current.mousePosition)) Fill(rect, new Color(0.65f, 0.88f, 1, 0.045f));
        return GUI.Button(rect, text, button);
    }

    private bool ActionButton(Rect rect, string text)
    {
        bool hover = GUI.enabled && rect.Contains(Event.current.mousePosition);
        Fill(rect, new Color(accent.r, accent.g, accent.b, GUI.enabled ? (hover ? 0.26f : 0.16f) : 0.06f));
        Fill(new Rect(rect.x, rect.yMax - 1, rect.width, 1), new Color(accent.r, accent.g, accent.b, GUI.enabled ? 0.8f : 0.2f));
        return GUI.Button(rect, text, button);
    }

    // Stiller varsayılan Unity düğme/alan görünümünü miras almaz.
    private GUIStyle TextStyle(int size, Color color, TextAnchor alignment = TextAnchor.UpperLeft)
    {
        GUIStyle style = new GUIStyle { font = GUI.skin.font, fontSize = size, alignment = alignment, wordWrap = true };
        foreach (var state in new[] { style.normal, style.hover, style.active, style.focused,
            style.onNormal, style.onHover, style.onActive, style.onFocused })
        { state.background = null; state.textColor = color; }
        return style;
    }

    private void CreateStyles()
    {
        Color white = new Color(0.9f, 0.95f, 1);
        label = TextStyle(22, white);
        small = TextStyle(16, new Color(0.66f, 0.75f, 0.83f));
        caption = TextStyle(13, new Color(0.6f, 0.74f, 0.8f));
        heading = TextStyle(38, white); heading.fontStyle = FontStyle.Bold;
        brand = TextStyle(66, white); brand.fontStyle = FontStyle.Bold;
        menu = TextStyle(25, white, TextAnchor.MiddleLeft); menu.hover.textColor = accent;
        button = TextStyle(15, white, TextAnchor.MiddleCenter);
        button.hover.textColor = button.onNormal.textColor = button.onHover.textColor = accent;
        field = TextStyle(22, white, TextAnchor.MiddleLeft);
        field.padding = new RectOffset(12, 12, 0, 0); field.wordWrap = false;
        number = TextStyle(92, white, TextAnchor.MiddleCenter);
    }

    private static void Fill(Rect rect, Color color)
    {
        Color previous = GUI.color; GUI.color = color;
        GUI.DrawTexture(rect, Texture2D.whiteTexture);
        GUI.color = previous;
    }

    private void Quit()
    {
#if UNITY_EDITOR
        UnityEditor.EditorApplication.isPlaying = false;
#else
        Application.Quit();
#endif
    }
}
