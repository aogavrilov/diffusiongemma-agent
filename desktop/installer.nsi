Unicode True
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!include "FileFunc.nsh"

!ifndef APP_SOURCE
  !error "APP_SOURCE must point to the PyInstaller application directory"
!endif
!ifndef OUTPUT_FILE
  !define OUTPUT_FILE "DiffusionGemmaAgentSetup-0.1.1.exe"
!endif
!ifndef REPO_ROOT
  !define REPO_ROOT ".."
!endif

!define APP_NAME "DiffusionGemma Agent"
!define APP_VERSION "0.1.1"
!define APP_PUBLISHER "DiffusionGemma Agent contributors"
!define APP_URL "https://github.com/aogavrilov/diffusiongemma-agent"
!define APP_REGKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\DiffusionGemmaAgent"

Name "${APP_NAME}"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\DiffusionGemmaAgent"
InstallDirRegKey HKCU "${APP_REGKEY}" "InstallLocation"
RequestExecutionLevel user
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "0.1.1.0"
VIAddVersionKey /LANG=1033 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "FileDescription" "DiffusionGemma Agent Windows installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Apache-2.0"

!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\DiffusionGemmaAgent.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch DiffusionGemma Agent"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${REPO_ROOT}\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "DiffusionGemma Agent (required)" SEC_CORE
  SectionIn RO
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File /r "${APP_SOURCE}\*"

  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\DiffusionGemma Agent"
  CreateShortcut "$SMPROGRAMS\DiffusionGemma Agent\DiffusionGemma Agent.lnk" "$INSTDIR\DiffusionGemmaAgent.exe"
  CreateShortcut "$SMPROGRAMS\DiffusionGemma Agent\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "${APP_REGKEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${APP_REGKEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${APP_REGKEY}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKCU "${APP_REGKEY}" "URLInfoAbout" "${APP_URL}"
  WriteRegStr HKCU "${APP_REGKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${APP_REGKEY}" "DisplayIcon" "$INSTDIR\DiffusionGemmaAgent.exe"
  WriteRegStr HKCU "${APP_REGKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${APP_REGKEY}" "NoModify" 1
  WriteRegDWORD HKCU "${APP_REGKEY}" "NoRepair" 1

  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKCU "${APP_REGKEY}" "EstimatedSize" "$0"
SectionEnd

Section /o "Desktop shortcut" SEC_DESKTOP
  SetShellVarContext current
  CreateShortcut "$DESKTOP\DiffusionGemma Agent.lnk" "$INSTDIR\DiffusionGemmaAgent.exe"
SectionEnd

LangString DESC_SEC_CORE ${LANG_ENGLISH} "The desktop app and standalone installer core. Python is included."
LangString DESC_SEC_DESKTOP ${LANG_ENGLISH} "Add a shortcut to the current user's desktop."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_CORE} $(DESC_SEC_CORE)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP} $(DESC_SEC_DESKTOP)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  SetShellVarContext current
  IfFileExists "$INSTDIR\dg-agent-core.exe" 0 +2
    ExecWait '"$INSTDIR\dg-agent-core.exe" stop'
  Delete "$DESKTOP\DiffusionGemma Agent.lnk"
  RMDir /r "$SMPROGRAMS\DiffusionGemma Agent"
  DeleteRegKey HKCU "${APP_REGKEY}"
  RMDir /r "$INSTDIR"
SectionEnd
