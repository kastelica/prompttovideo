# PowerShell script to connect to Cloud SQL database
# PostgreSQL connection details
$DB_HOST = "34.46.33.136"
$DB_PORT = "5432"
$DB_NAME = "prompttovideo"
$DB_USER = "prompttovideo"
$DB_PASSWORD = "PromptToVideo2024!"

Write-Host "🔗 Connecting to Cloud SQL database..." -ForegroundColor Green
Write-Host "Host: $DB_HOST" -ForegroundColor Yellow
Write-Host "Database: $DB_NAME" -ForegroundColor Yellow
Write-Host "User: $DB_USER" -ForegroundColor Yellow
Write-Host ""

# Set the PGPASSWORD environment variable for psql
$env:PGPASSWORD = $DB_PASSWORD

# Connect using psql
try {
    & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h $DB_HOST -p $DB_PORT -d $DB_NAME -U $DB_USER
} catch {
    Write-Host "❌ Connection failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting tips:" -ForegroundColor Yellow
    Write-Host "1. Make sure your IP is authorized in Cloud SQL"
    Write-Host "2. Check if the database is running"
    Write-Host "3. Verify the connection details"
}

# Clear the password from environment
$env:PGPASSWORD = "" 