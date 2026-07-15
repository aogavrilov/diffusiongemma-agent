@echo off
if exist "%~dp0python.exe" goto adjacent_python
python -m diffusiongemma_agent %*
exit /b %ERRORLEVEL%

:adjacent_python
"%~dp0python.exe" -m diffusiongemma_agent %*
exit /b %ERRORLEVEL%
