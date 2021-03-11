;---------------------------------
;Includes
!include MUI2.nsh
!include "FileAssociation.nsh"

;---------------------------------
;About
Name "EV3Sim"
OutFile "one_click_no_admin.exe"
Unicode true
InstallDirRegKey HKCU "Software\EV3Sim" ""

Function .onInit
StrCpy $InstDir "$LocalAppData\$(^Name)"
SetShellVarContext Current
FunctionEnd 

;---------------------------------
;Styling

!define MUI_ICON "ev3sim\assets\Logo.ico"
!define MUI_UNICON "ev3sim\assets\Logo.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "ev3sim\assets\Logo.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "ev3sim\assets\Logo.bmp"
!define MUI_HEADERIMAGE_RIGHT
!define MUI_WELCOMEFINISHPAGE_BITMAP "ev3sim\assets\installer_preview.bmp"

!define MUI_PAGE_HEADER_TEXT "EV3Sim"
!define MUI_PAGE_HEADER_SUBTEXT "Robotics Simulator"

!define MUI_DIRECTORYPAGE_VARIABLE $InstDir

!define MUI_WELCOMEPAGE_TITLE "Welcome to EV3Sim!"
!define MUI_WELCOMEPAGE_TEXT "You'll need to select a few options before you can get started with ev3sim."

!define MUI_LICENSEPAGE_TEXT_TOP "You must agree to the following (short) license before you can use EV3Sim."

!define MUI_INSTFILESPAGE_FINISHHEADER_TEXT "Installation Complete!"
!define MUI_INSTFILESPAGE_ABORTHEADER_TEXT "Installation Aborted."

!define MUI_FINISHPAGE_TITLE "All Done!"
!define MUI_FINISHPAGE_RUN "$InstDir\ev3sim.exe"
!define MUI_FINISHPAGE_SHOWREADME "https://ev3sim.mhsrobotics.club/"
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
SetOutPath "$InstDir"
File /nonfatal /a /r "dist\ev3sim\"
WriteRegStr HKCU "Software\EV3Sim" "" $InstDir
IfFileExists "$InstDir\ev3sim\user_config.yaml" update
;Generate the default user config if not in update.
CopyFiles "$InstDir\ev3sim\presets\default_config.yaml" "$InstDir\ev3sim\user_config.yaml"
;Start Menu
createDirectory "$SMPROGRAMS\MHS_Robotics"
createShortCut "$SMPROGRAMS\MHS_Robotics\EV3Sim.lnk" "$InstDir\ev3sim.exe" "" "$InstDir\ev3sim.exe" 0
;File Associations
;Open sims by default.
${registerExtensionOpen} "$InstDir\ev3sim.exe" ".sim" "ev3sim.sim_file"
${registerExtensionEdit} "$InstDir\ev3sim.exe" ".sim" "ev3sim.sim_file"
;Open bots by default.
${registerExtensionOpen} "$InstDir\ev3sim.exe" ".bot" "ev3sim.bot_file"
update:
;Create uninstaller
WriteUninstaller "$InstDir\Uninstall.exe"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EV3Sim" "DisplayName" "EV3Sim - Robotics Simulator"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EV3Sim" "UninstallString" "$\"$InstDir\Uninstall.exe$\""
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EV3Sim" "QuietUninstallString" "$\"$InstDir\Uninstall.exe$\" /S"
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
Delete /REBOOTOK "$InstDir\Uninstall.exe"
RMDir /R /REBOOTOK "$InstDir"
DeleteRegKey /ifempty HKCU "Software\EV3Sim"
DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\EV3Sim"
;File Associations
${unregisterExtension} ".sim" "ev3sim.sim_file"
${unregisterExtension} ".bot" "ev3sim.bot_file"
;Remove Start Menu launcher
Delete /REBOOTOK "$SMPROGRAMS\MHS_Robotics\EV3Sim.lnk"
;Try to remove the Start Menu folder - this will only happen if it is empty
RMDir /R /REBOOTOK "$SMPROGRAMS\MHS_Robotics"
SectionEnd
