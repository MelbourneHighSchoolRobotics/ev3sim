;---------------------------------
;Includes
!include MUI2.nsh
RequestExecutionLevel highest

;---------------------------------
;About
Name "EV3Sim"
OutFile "EV3Sim_installer.exe"
Unicode true
InstallDirRegKey HKCU "Software\EV3Sim" ""
Var IsAdminMode
!macro SetAdminMode
StrCpy $IsAdminMode 1
SetShellVarContext All
${IfThen} $InstDir == "" ${|} StrCpy $InstDir "$Programfiles\$(^Name)" ${|}
!macroend
!macro SetUserMode
StrCpy $IsAdminMode 0
SetShellVarContext Current
${IfThen} $InstDir == "" ${|} StrCpy $InstDir "$LocalAppData\Programs\$(^Name)" ${|}
!macroend

Function .onInit
UserInfo::GetAccountType
Pop $0
${IfThen} $0 != "Admin" ${|} Goto setmode_currentuser ${|}

!insertmacro SetAdminMode
Goto finalize_mode

setmode_currentuser:
!insertmacro SetUserMode

finalize_mode:
FunctionEnd 

;---------------------------------
;Styling

!define MUI_ICON "ev3sim\assets\Logo.ico"
!define MUI_UNICON "ev3sim\assets\Logo.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "ev3sim\assets\Logo.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "ev3sim\assets\Logo.bmp"
!define MUI_HEADERIMAGE_RIGHT

!define MUI_PAGE_HEADER_TEXT "EV3Sim"
!define MUI_PAGE_HEADER_SUBTEXT "Robotics Simulator"

!define MUI_WELCOMEPAGE_TITLE "Welcome to EV3Sim!"
!define MUI_WELCOMEPAGE_TEXT "You'll need to select a few options before you can get started with ev3sim."

!define MUI_LICENSEPAGE_TEXT_TOP "You must agree to the following (short) license before you can use EV3Sim."

!define MUI_INSTFILESPAGE_FINISHHEADER_TEXT "Installation Complete!"
!define MUI_INSTFILESPAGE_ABORTHEADER_TEXT "Installation Aborted."

!define MUI_FINISHPAGE_TITLE "All Done!"
!define MUI_FINISHPAGE_RUN "$INSTDIR\ev3sim.exe"
!define MUI_FINISHPAGE_SHOWREADME "https://ev3sim.mhscsr.club/"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Go to documentation."

;---------------------------------
;Pages

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages
 
!insertmacro MUI_LANGUAGE "English"

;---------------------------------
;Sections
Section "Dummy Section" SecDummy
SetOutPath "$INSTDIR"
File /nonfatal /a /r "dist\ev3sim\"
WriteRegStr HKCU "Software\EV3Sim" "" $INSTDIR
;Start Menu
createDirectory "$SMPROGRAMS\MHS_Robotics"
createShortCut "$SMPROGRAMS\MHS_Robotics\EV3Sim.lnk" "$INSTDIR\ev3sim.exe" "" "$INSTDIR\ev3sim.exe" 0
;Create uninstaller
WriteUninstaller "$INSTDIR\Uninstall.exe"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EV3Sim" "DisplayName" "EV3Sim - Robotics Simulator"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EV3Sim" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EV3Sim" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
SectionEnd

;---------------------------------
;Descriptions

;Language strings
LangString DESC_SecDummy ${LANG_ENGLISH} "A test section."

;Assign language strings to sections
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
!insertmacro MUI_DESCRIPTION_TEXT ${SecDummy} $(DESC_SecDummy)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;---------------------------------
;Uninstaller Section

Section "Uninstall"
Delete /REBOOTOK "$INSTDIR\Uninstall.exe"
RMDir /R /REBOOTOK "$INSTDIR"
DeleteRegKey /ifempty HKCU "Software\EV3Sim"
DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EV3Sim"
;Remove Start Menu launcher
Delete /REBOOTOK "$SMPROGRAMS\MHS_Robotics\EV3Sim.lnk"
;Try to remove the Start Menu folder - this will only happen if it is empty
RMDir /R /REBOOTOK "$SMPROGRAMS\MHS_Robotics"
SectionEnd
