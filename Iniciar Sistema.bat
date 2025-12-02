@echo off
TITLE Dayanne Coutinho Advocacia - Iniciando Sistema...
echo ---------------------------------------------------
echo      SISTEMA JURIDICO DAYANNE COUTINHO
echo ---------------------------------------------------
echo.
echo Iniciando o servidor de dados...
echo Por favor, nao feche esta janela enquanto usar o sistema.
echo.
echo O navegador abrira automaticamente em alguns segundos...
echo.

:: Navega para a pasta onde o arquivo está salvo
cd /d "%~dp0"

:: Executa o Streamlit
streamlit run app.py