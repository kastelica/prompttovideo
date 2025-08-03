@echo off
echo 🔗 Connecting to Cloud SQL database...
echo Host: 34.46.33.136
echo Database: prompttovideo
echo User: prompttovideo
echo.

set PGPASSWORD=PromptToVideo2024!
"C:\Program Files\PostgreSQL\17\bin\psql.exe" -h 34.46.33.136 -p 5432 -d prompttovideo -U prompttovideo
set PGPASSWORD=

echo.
echo Connection closed.
pause 