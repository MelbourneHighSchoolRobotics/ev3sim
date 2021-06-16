;---------------------------------
;Includes
!include MUI2.nsh
!include "FileAssociation.nsh"

;---------------------------------
;About
Name "EV3Sim"
OutFile "installer.exe"
Unicode true
InstallDirRegKey HKCU "Software\EV3Sim" ""

Var ExeLocation

Function .onInit
StrCpy $InstDir "$LocalAppData\$(^Name)"
StrCpy $ExeLocation "$InstDir\python_embed\Scripts\ev3sim.exe"
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
!define MUI_FINISHPAGE_RUN "$ExeLocation"
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
; Remove previous installation
IfFileExists "$InstDir\python_embed\Lib\site-packages\ev3sim\user_config.yaml" update no_update
update:
CopyFiles "$InstDir\python_embed\Lib\site-packages\ev3sim\user_config.yaml" "$InstDir\default_config.yaml"
no_update:
RMDir /r "$InstDir\python_embed"
SetOutPath "$InstDir"
File /nonfatal /a /r "dist\"
WriteRegStr HKCU "Software\EV3Sim" "" $InstDir

;Run pip install process. pythonw seems to not finish correctly, and so ev3sim doesn't get installed.
;To use test.pypi: '"$InstDir\python_embed\python.exe" -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ev3sim==2.1.8.post1'
ExecDos::exec '"$InstDir\python_embed\python.exe" -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org ev3sim' "" "$InstDir\pip.log"
Pop $0
StrCmp "0" $0 fine

MessageBox MB_OK "Installation failed, check '$InstDir\pip.log'"
Quit

fine:

;Do user_config stuff
IfFileExists "$InstDir\default_config.yaml" second_update
CopyFiles "$InstDir\python_embed\Lib\site-packages\ev3sim\presets\default_config.yaml" "$InstDir\default_config.yaml"
second_update:
CopyFiles "$InstDir\default_config.yaml" "$InstDir\python_embed\Lib\site-packages\ev3sim\user_config.yaml"

;Start Menu
createDirectory "$SMPROGRAMS\MHS_Robotics"
createShortCut "$SMPROGRAMS\MHS_Robotics\EV3Sim.lnk" "$ExeLocation" "" "$ExeLocation" 0
;File Associations
;URL associations for custom tasks.
WriteRegStr HKCR "ev3simc" "" "URL:ev3simc Protocol"
WriteRegStr HKCR "ev3simc" "URL Protocol" ""
WriteRegStr HKCR "ev3simc\shell" "" ""
WriteRegStr HKCR "ev3simc\DefaultIcon" "" "$ExeLocation,0"
WriteRegStr HKCR "ev3simc\shell\open" "" ""
WriteRegStr HKCR "ev3simc\shell\open\command" "" '"$ExeLocation" "%l" --custom-url'
;Open sims by default.
${registerExtensionOpen} "$ExeLocation" ".sim" "ev3sim.sim_file"
${registerExtensionEdit} "$ExeLocation" ".sim" "ev3sim.sim_file"
;Open bots by default.
${registerExtensionOpen} "$ExeLocation" ".bot" "ev3sim.bot_file"
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
