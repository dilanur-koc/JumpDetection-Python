using System;
using System.Collections;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.Networking;

// Unity SQL'e doğrudan bağlanmaz. Bütün hesap ve sonuç işlemleri API üzerinden geçer.
// Şifre, token ve kullanıcı sonuçları PlayerPrefs'e veya dosyaya yazılmaz.
public sealed class GameAccountClient : MonoBehaviour
{
    [Serializable] public sealed class Profile { public int id; public string userName, createdAtUtc; }
    [Serializable] public sealed class GameResult
    {
        public long id;
        public int levelNumber, score, durationMs;
        public string inputSource, createdAtUtc;
        public bool completed;
    }
    [Serializable] public sealed class Progress { public int levelNumber; public bool isCompleted; public string updatedAtUtc; }
    [Serializable] private sealed class Credentials { public string userName, password; }
    [Serializable] private sealed class TokenReply { public string accessToken; public long expiresIn; }
    [Serializable] private sealed class ResultList { public GameResult[] items; }
    [Serializable] private sealed class ProgressList { public Progress[] items; }
    [Serializable] private sealed class NewResult
    {
        public int levelNumber, score, durationMs;
        public string inputSource;
        public bool completed;
    }
    private sealed class Reply { public long status; public string body, error; public bool Ok => status >= 200 && status < 300 && error == null; }

    public Profile User { get; private set; }
    public GameResult[] Results { get; private set; } = new GameResult[0];
    public Progress[] Levels { get; private set; } = new Progress[0];
    public bool IsBusy { get; private set; }
    public string Message { get; private set; } = "Sign in or create an account.";
    public bool IsAuthenticated => User != null && accessToken != null && DateTime.UtcNow < expiresAtUtc;

    private string baseUrl, accessToken;
    private DateTime expiresAtUtc;
    private UnityWebRequest activeRequest;

    public void Initialize(string url) { baseUrl = url.TrimEnd('/'); }

    public void Authenticate(string name, string password, bool register)
    {
        if (IsBusy) return;
        name = name.Trim().Normalize();
        if (!Regex.IsMatch(name, @"\A[\p{L}\p{N}_.-]{3,32}\z"))
        {
            Message = "Use 3–32 letters, numbers, dots, hyphens or underscores for your username.";
            return;
        }
        if (string.IsNullOrWhiteSpace(password) || password.Length < 8 || password.Length > 128)
        {
            Message = "Your password must contain 8–128 characters.";
            return;
        }
        StartCoroutine(AuthenticateRoutine(new Credentials { userName = name, password = password }, register));
    }

    private IEnumerator AuthenticateRoutine(Credentials credentials, bool register)
    {
        IsBusy = true;
        try
        {
            Reply reply = null;
            string json = JsonUtility.ToJson(credentials);
            if (register)
            {
                Message = "Creating account…";
                yield return Send("/api/auth/register", "POST", json, null, value => reply = value);
                if (!reply.Ok) { Message = Explain(reply, true); yield break; }
            }
            Message = "Signing in…";
            yield return Send("/api/auth/login", "POST", json, null, value => reply = value);
            if (!reply.Ok) { Message = Explain(reply, false); yield break; }
            TokenReply token = Parse<TokenReply>(reply.body);
            if (token == null || string.IsNullOrEmpty(token.accessToken) || token.expiresIn <= 0 || token.expiresIn > 86400)
            {
                Message = "The sign-in response could not be read.";
                yield break;
            }
            accessToken = token.accessToken;
            expiresAtUtc = DateTime.UtcNow.AddSeconds(token.expiresIn);
            yield return Send("/api/auth/me", "GET", null, accessToken, value => reply = value);
            Profile profile = reply.Ok ? Parse<Profile>(reply.body) : null;
            if (profile == null || profile.id <= 0 || string.IsNullOrEmpty(profile.userName))
            {
                ClearSession();
                Message = reply.Ok ? "Your profile could not be read." : Explain(reply, false);
                yield break;
            }
            User = profile;
            credentials.password = null;
            Message = "Signed in as " + User.userName + ".";
            yield return RefreshRoutine();
        }
        finally { IsBusy = false; credentials.password = null; }
    }

    public void Refresh()
    {
        if (IsAuthenticated && !IsBusy) StartCoroutine(RefreshWithBusy());
    }

    private IEnumerator RefreshWithBusy()
    {
        IsBusy = true;
        try { yield return RefreshRoutine(); }
        finally { IsBusy = false; }
    }

    private IEnumerator RefreshRoutine()
    {
        Reply reply = null;
        yield return Send("/api/game-results", "GET", null, accessToken, value => reply = value);
        if (!reply.Ok) { HandleAccountError(reply); yield break; }
        ResultList results = Parse<ResultList>("{\"items\":" + reply.body + "}");
        if (results == null || results.items == null) { Message = "Your run history could not be read."; yield break; }
        Results = results.items;
        yield return Send("/api/progress", "GET", null, accessToken, value => reply = value);
        if (!reply.Ok) { HandleAccountError(reply); yield break; }
        ProgressList progress = Parse<ProgressList>("{\"items\":" + reply.body + "}");
        if (progress == null || progress.items == null) { Message = "Your level progress could not be read."; yield break; }
        Levels = progress.items;
    }

    // Skor şimdilik ilerleme yüzdesinden üretilir. Kullanıcı ID'sini sunucu token'dan bulur.
    // POST otomatik tekrarlanmaz. Yanıt kaybolursa aynı turun iki kez eklenmesi önlenir.
    public void SaveRound(int score, int durationMs, string source, bool completed)
    {
        if (!IsAuthenticated || IsBusy) return;
        var result = new NewResult { levelNumber = 1, score = score, durationMs = durationMs, inputSource = source, completed = completed };
        StartCoroutine(SaveRoutine(result));
    }

    private IEnumerator SaveRoutine(NewResult result)
    {
        IsBusy = true;
        try
        {
            Message = "Saving run…";
            Reply reply = null;
            yield return Send("/api/game-results", "POST", JsonUtility.ToJson(result), accessToken, value => reply = value);
            if (!reply.Ok)
            {
                HandleAccountError(reply);
                if (reply.status == 0) Message = "No save confirmation received. Refresh your recent runs to check the result.";
                yield break;
            }
            Message = "Run saved. Your five latest results are kept.";
            yield return RefreshRoutine();
        }
        finally { IsBusy = false; }
    }

    public void Logout()
    {
        if (IsBusy) return;
        ClearSession();
        Message = "Signed out.";
    }

    private void ClearSession()
    {
        accessToken = null;
        User = null;
        Results = new GameResult[0];
        Levels = new Progress[0];
    }

    private void Update()
    {
        if (accessToken != null && DateTime.UtcNow >= expiresAtUtc && !IsBusy)
        {
            ClearSession();
            Message = "Your session has expired. Please sign in again.";
        }
    }

    private void HandleAccountError(Reply reply)
    {
        if (reply.status == 401) ClearSession();
        Message = reply.status == 401 ? "Your session has expired. Please sign in again." : Explain(reply, false);
    }

    private static string Explain(Reply reply, bool registering)
    {
        if (reply.status == 409) return "This username is taken. Choose another name or sign in.";
        if (reply.status == 401) return "Incorrect username or password.";
        if (reply.status == 429) return "Too many attempts. Please try again in a minute.";
        if (reply.status == 400) return "Check your details: username 3–32 characters, password 8–128 characters.";
        if (reply.status == 503) return "The database is unavailable. Please try again later.";
        if (reply.status == 0) return "Unable to connect to the game service. Please try again shortly.";
        return registering ? "Unable to create your account. Please try again." : "Unable to complete the request. Please try again.";
    }

    // Coroutine, ağ yanıtını beklerken Unity'nin görüntü ve fizik döngüsünü durdurmaz.
    private IEnumerator Send(string path, string method, string json, string token, Action<Reply> completed)
    {
        Uri uri;
        if (!Uri.TryCreate(baseUrl + path, UriKind.Absolute, out uri)
            || (uri.Scheme != "http" && uri.Scheme != "https")
            || (uri.Scheme == "http" && !uri.IsLoopback))
        {
            completed(new Reply { status = 0, error = "Invalid service address." });
            yield break;
        }
        using (var request = new UnityWebRequest(uri.AbsoluteUri, method))
        {
            request.downloadHandler = new DownloadHandlerBuffer();
            request.timeout = 10;
            request.redirectLimit = 0;
            if (json != null)
            {
                request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
                request.SetRequestHeader("Content-Type", "application/json; charset=utf-8");
            }
            if (token != null) request.SetRequestHeader("Authorization", "Bearer " + token);
            activeRequest = request;
            try { yield return request.SendWebRequest(); }
            finally { activeRequest = null; }
            completed(new Reply
            {
                status = request.responseCode,
                body = request.downloadHandler.text,
                error = request.result == UnityWebRequest.Result.Success ? null : request.error
            });
        }
    }

    private static T Parse<T>(string json) where T : class
    {
        try { return JsonUtility.FromJson<T>(json); }
        catch (ArgumentException) { return null; }
    }

    private void OnDisable()
    {
        if (activeRequest != null) activeRequest.Abort();
        StopAllCoroutines();
        IsBusy = false;
    }
}
