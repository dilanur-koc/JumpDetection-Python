-- İlk kurulum: SSMS'te tüm dosyayı çalıştır. Mevcut kullanıcı/veri tabloları silinmez.
-- Şema, 5 Kasım 2026'da çalışan RadarPlatformGameDb yapısıyla karşılaştırılmıştır.
IF DB_ID(N'RadarPlatformGameDb') IS NULL
    EXEC(N'CREATE DATABASE RadarPlatformGameDb;');
GO
USE RadarPlatformGameDb;
GO
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    -- Kullanıcı adı tekildir. Şifrenin kendisi değil, API'nin ürettiği özet tutulur.
    IF OBJECT_ID(N'dbo.Users', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.Users
        (
            Id INT IDENTITY(1,1) CONSTRAINT PK_Users PRIMARY KEY,
            UserName NVARCHAR(32) COLLATE Latin1_General_100_CI_AS_SC NOT NULL,
            PasswordHash NVARCHAR(512) NOT NULL,
            CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_Users_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
            CONSTRAINT UQ_Users_UserName UNIQUE (UserName),
            CONSTRAINT CK_Users_UserName CHECK
                (LEN(UserName) BETWEEN 3 AND 32 AND DATALENGTH(UserName) = DATALENGTH(TRIM(UserName))),
            CONSTRAINT CK_Users_PasswordHash CHECK (LEN(PasswordHash) > 0)
        );
    END;

    -- Her satır tamamlanan veya kaybedilen bir oyun turudur.
    IF OBJECT_ID(N'dbo.GameResults', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.GameResults
        (
            Id BIGINT IDENTITY(1,1) CONSTRAINT PK_GameResults PRIMARY KEY,
            UserId INT NOT NULL CONSTRAINT FK_GameResults_Users REFERENCES dbo.Users(Id),
            LevelNumber INT NOT NULL CONSTRAINT CK_GameResults_LevelNumber CHECK (LevelNumber >= 1),
            Score INT NOT NULL CONSTRAINT CK_GameResults_Score CHECK (Score >= 0),
            DurationMs INT NOT NULL CONSTRAINT CK_GameResults_DurationMs CHECK (DurationMs >= 0),
            InputSource VARCHAR(16) NOT NULL CONSTRAINT CK_GameResults_InputSource
                CHECK (InputSource IN ('keyboard', 'simulator', 'radar')),
            Completed BIT NOT NULL,
            CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_GameResults_CreatedAtUtc DEFAULT SYSUTCDATETIME()
        );
        CREATE INDEX IX_GameResults_User_Recent
            ON dbo.GameResults (UserId, CreatedAtUtc DESC, Id DESC);
    END;

    -- Geçmiş sonuçlar temizlense de tamamlanan bölüm bilgisi korunur.
    IF OBJECT_ID(N'dbo.UserProgress', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.UserProgress
        (
            UserId INT NOT NULL CONSTRAINT FK_UserProgress_Users REFERENCES dbo.Users(Id),
            LevelNumber INT NOT NULL CONSTRAINT CK_UserProgress_LevelNumber CHECK (LevelNumber >= 1),
            IsCompleted BIT NOT NULL CONSTRAINT DF_UserProgress_IsCompleted DEFAULT 0,
            UpdatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_UserProgress_UpdatedAtUtc DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_UserProgress PRIMARY KEY (UserId, LevelNumber)
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

-- API, sonuclari bu prosedurle kaydedecek.
-- Sonuc ekleme, son 5 kaydi tutma ve ilerlemeyi guncelleme birlikte tamamlanir.
-- Tablolara elle INSERT yapilmasi bu proseduru calistirmaz.
CREATE OR ALTER PROCEDURE dbo.SaveGameResult
    @UserId INT,
    @LevelNumber INT,
    @Score INT,
    @DurationMs INT,
    @InputSource VARCHAR(16),
    @Completed BIT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Prosedur kendi islem sinirini yonetir. API bunu ayri bir komut olarak cagirir.
    IF @@TRANCOUNT <> 0
        THROW 50000, N'SaveGameResult acik bir transaction icinden cagrilamaz.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @AccountId INT;

        -- Ayni kullanici icin iki kayit ayni anda gelirse sira ile islenir.
        -- Kilit sonuc eklenmeden once alinir ve COMMIT'e kadar tutulur.
        SELECT @AccountId = Id
        FROM dbo.Users WITH (UPDLOCK, HOLDLOCK)
        WHERE Id = @UserId;

        IF @AccountId IS NULL
            THROW 50001, N'Kullanici bulunamadi.', 1;

        INSERT INTO dbo.GameResults
            (UserId, LevelNumber, Score, DurationMs, InputSource, Completed)
        VALUES
            (@UserId, @LevelNumber, @Score, @DurationMs, @InputSource, @Completed);

        DECLARE @ResultId BIGINT = CONVERT(BIGINT, SCOPE_IDENTITY());

        -- Kullanicinin en yeni 5 sonucu saklanir. Tarih ayniysa buyuk Id daha yenidir.
        ;WITH OrderedResults AS
        (
            SELECT Id,
                ROW_NUMBER() OVER (ORDER BY CreatedAtUtc DESC, Id DESC) AS Position
            FROM dbo.GameResults
            WHERE UserId = @UserId
        )
        DELETE FROM OrderedResults WHERE Position > 5;

        -- Daha once tamamlanan bolum, sonraki basarisiz denemeyle kilitlenmez.
        UPDATE dbo.UserProgress
        SET IsCompleted = CASE WHEN @Completed = 1 THEN 1 ELSE IsCompleted END,
            UpdatedAtUtc = SYSUTCDATETIME()
        WHERE UserId = @UserId AND LevelNumber = @LevelNumber;

        IF @@ROWCOUNT = 0
        BEGIN
            INSERT INTO dbo.UserProgress (UserId, LevelNumber, IsCompleted)
            VALUES (@UserId, @LevelNumber, @Completed);
        END;

        COMMIT TRANSACTION;
        SELECT @ResultId AS ResultId;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
