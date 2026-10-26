#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shlobj.h>
#include <shellapi.h>
#include <wrl.h>
#include <WebView2.h>
#include <filesystem>
#include <string>
#include <thread>
#include <regex>
#include <vector>
#include <fstream>
using Microsoft::WRL::ComPtr;
using Microsoft::WRL::Callback;
namespace fs=std::filesystem;
#ifdef STUDY_PREVIEW
const wchar_t* title=L"日常学习预览版";
const wchar_t* channel=L"preview";
#else
const wchar_t* title=L"日常学习";
const wchar_t* channel=L"stable";
#endif
constexpr UINT WM_READY=WM_APP+1,WM_FAILED=WM_APP+2;
HWND windowHandle=nullptr;HANDLE backend=nullptr,job=nullptr,instance=nullptr;
ComPtr<ICoreWebView2Controller> controller;ComPtr<ICoreWebView2> web;
fs::path dataRoot;std::wstring origin;bool closing=false;
std::wstring quote(const std::wstring& v){
 std::wstring r=L"\"";size_t n=0;
 for(wchar_t c:v){if(c==L'\\'){++n;continue;}if(c==L'\"')r.append(n*2+1,L'\\');else r.append(n,L'\\');n=0;r+=c;}
 r.append(n*2,L'\\');return r+L"\"";
}
bool own(const std::wstring& url){return url==origin||url.rfind(origin+L"/",0)==0||url.rfind(origin+L"#",0)==0;}
void external(const std::wstring& url){if(url.rfind(L"https://",0)==0||url.rfind(L"http://",0)==0)ShellExecuteW(windowHandle,L"open",url.c_str(),nullptr,nullptr,SW_SHOWNORMAL);}
void fail(const wchar_t* message){MessageBoxW(windowHandle,message,title,MB_OK|MB_ICONERROR);}
void showWeb(const std::wstring& url){
 origin=url;fs::create_directories(dataRoot/L"WebView2");
 HRESULT hr=CreateCoreWebView2EnvironmentWithOptions(nullptr,(dataRoot/L"WebView2").c_str(),nullptr,
  Callback<ICoreWebView2CreateCoreWebView2EnvironmentCompletedHandler>([](HRESULT result,ICoreWebView2Environment* env)->HRESULT{
   if(FAILED(result)||!env){fail(L"无法启动系统 WebView2。请安装微软官方 WebView2 Evergreen Runtime 后重试。\nhttps://developer.microsoft.com/microsoft-edge/webview2/");return S_OK;}
   return env->CreateCoreWebView2Controller(windowHandle,Callback<ICoreWebView2CreateCoreWebView2ControllerCompletedHandler>([](HRESULT result,ICoreWebView2Controller* value)->HRESULT{
    if(FAILED(result)||!value){fail(L"无法创建学习窗口，请重启应用。");return S_OK;}
    controller=value;controller->get_CoreWebView2(&web);RECT bounds;GetClientRect(windowHandle,&bounds);controller->put_Bounds(bounds);
    ComPtr<ICoreWebView2Settings> settings;web->get_Settings(&settings);settings->put_IsStatusBarEnabled(FALSE);
    EventRegistrationToken token;
    web->add_NavigationStarting(Callback<ICoreWebView2NavigationStartingEventHandler>([](ICoreWebView2*,ICoreWebView2NavigationStartingEventArgs* args)->HRESULT{
     LPWSTR raw=nullptr;args->get_Uri(&raw);std::wstring url=raw?raw:L"";CoTaskMemFree(raw);
     if(!own(url)){args->put_Cancel(TRUE);BOOL user=FALSE;args->get_IsUserInitiated(&user);if(user)external(url);}return S_OK;
    }).Get(),&token);
    web->add_NewWindowRequested(Callback<ICoreWebView2NewWindowRequestedEventHandler>([](ICoreWebView2*,ICoreWebView2NewWindowRequestedEventArgs* args)->HRESULT{
     args->put_Handled(TRUE);LPWSTR raw=nullptr;args->get_Uri(&raw);std::wstring url=raw?raw:L"";CoTaskMemFree(raw);
     BOOL user=FALSE;args->get_IsUserInitiated(&user);if(own(url))web->Navigate(url.c_str());else if(user)external(url);return S_OK;
    }).Get(),&token);
    web->add_ProcessFailed(Callback<ICoreWebView2ProcessFailedEventHandler>([](ICoreWebView2*,ICoreWebView2ProcessFailedEventArgs*)->HRESULT{fail(L"页面进程已停止，请退出并重新启动应用。学习记录会保留。");return S_OK;}).Get(),&token);
    SetTimer(windowHandle,2,500,nullptr);
    return web->Navigate(origin.c_str());
   }).Get());
  }).Get());
 if(FAILED(hr)){
  if(MessageBoxW(windowHandle,L"需要微软 WebView2 运行时。打开微软官方下载页面？",title,MB_YESNO|MB_ICONINFORMATION)==IDYES)external(L"https://developer.microsoft.com/microsoft-edge/webview2/");
 }
}
void startBackend(){
 wchar_t exePath[32768];GetModuleFileNameW(nullptr,exePath,32768);auto exe=fs::path(exePath).parent_path()/L"backend/study-backend.exe";
 fs::create_directories(dataRoot);
 SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES),nullptr,TRUE};HANDLE readPipe=nullptr,writePipe=nullptr;
 if(!CreatePipe(&readPipe,&writePipe,&security,0)){PostMessageW(windowHandle,WM_FAILED,0,0);return;}
 SetHandleInformation(readPipe,HANDLE_FLAG_INHERIT,0);
 auto log=dataRoot/L"native-backend.log";HANDLE error=CreateFileW(log.c_str(),FILE_APPEND_DATA,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
 STARTUPINFOW si{};si.cb=sizeof(si);si.dwFlags=STARTF_USESTDHANDLES;si.hStdOutput=writePipe;si.hStdError=error;si.hStdInput=GetStdHandle(STD_INPUT_HANDLE);
 std::wstring cmd=quote(exe.wstring())+L" --root "+quote(dataRoot.wstring())+L" --port 0 --no-legacy --channel "+channel+L" --parent-pid "+std::to_wstring(GetCurrentProcessId());
 PROCESS_INFORMATION pi{};
 if(!CreateProcessW(exe.c_str(),cmd.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW|CREATE_SUSPENDED,nullptr,exe.parent_path().c_str(),&si,&pi)){
  CloseHandle(writePipe);CloseHandle(readPipe);if(error!=INVALID_HANDLE_VALUE)CloseHandle(error);PostMessageW(windowHandle,WM_FAILED,0,0);return;
 }
 backend=pi.hProcess;job=CreateJobObjectW(nullptr,nullptr);JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};limits.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
 bool assigned=job&&SetInformationJobObject(job,JobObjectExtendedLimitInformation,&limits,sizeof(limits))&&AssignProcessToJobObject(job,pi.hProcess);
 if(!assigned){TerminateProcess(pi.hProcess,1);CloseHandle(pi.hThread);CloseHandle(writePipe);CloseHandle(readPipe);if(error!=INVALID_HANDLE_VALUE)CloseHandle(error);PostMessageW(windowHandle,WM_FAILED,0,0);return;}
 ResumeThread(pi.hThread);CloseHandle(pi.hThread);CloseHandle(writePipe);if(error!=INVALID_HANDLE_VALUE)CloseHandle(error);
 std::thread([readPipe](){
  std::string line;char c;DWORD read=0;
  while(line.size()<16384&&ReadFile(readPipe,&c,1,&read,nullptr)&&read){if(c=='\n')break;line+=c;}
  std::smatch match;std::regex pattern("\\\"url\\\"\\s*:\\s*\\\"(http://127\\.0\\.0\\.1:([0-9]{1,5}))\\\"");
  if(std::regex_search(line,match,pattern)){
   int port=std::stoi(match[2].str());if(port>0&&port<=65535){std::string url=match[1];auto* value=new std::wstring(url.begin(),url.end());if(!PostMessageW(windowHandle,WM_READY,0,reinterpret_cast<LPARAM>(value)))delete value;}
   else PostMessageW(windowHandle,WM_FAILED,0,0);
  }else PostMessageW(windowHandle,WM_FAILED,0,0);
  char buffer[4096];while(ReadFile(readPipe,buffer,sizeof(buffer),&read,nullptr)&&read){}CloseHandle(readPipe);
 }).detach();
 SetTimer(windowHandle,1,30000,nullptr);
}
LRESULT CALLBACK WindowProc(HWND h,UINT m,WPARAM w,LPARAM l){
 switch(m){
 case WM_READY:{KillTimer(h,1);auto* value=reinterpret_cast<std::wstring*>(l);showWeb(*value);delete value;return 0;}
 case WM_FAILED:KillTimer(h,1);fail(L"学习服务启动失败。请确认没有另一个窗口使用相同数据，并检查数据目录中的 native-backend.log。关闭窗口后重试。");return 0;
 case WM_TIMER:
  if(w==1){KillTimer(h,1);fail(L"启动超过30秒。请关闭应用，检查数据目录权限后重试。");}
  if(w==2&&web){web->ExecuteScript(L"Boolean(window.ReleaseUI && document.querySelector('h1') && document.querySelector('h1').textContent.trim())",Callback<ICoreWebView2ExecuteScriptCompletedHandler>([](HRESULT result,LPCWSTR value)->HRESULT{
   if(SUCCEEDED(result)&&value&&std::wstring(value)==L"true"){
    KillTimer(windowHandle,2);
    std::ofstream state(dataRoot/L".window-state.json");state<<"{\"ready\":true}";
   }return S_OK;
  }).Get());}return 0;
 case WM_SIZE:if(controller){RECT r;GetClientRect(h,&r);controller->put_Bounds(r);}return 0;
 case WM_GETMINMAXINFO:{auto* info=reinterpret_cast<MINMAXINFO*>(l);info->ptMinTrackSize={980,700};return 0;}
 case WM_CLOSE:DestroyWindow(h);return 0;
 case WM_DESTROY:closing=true;if(controller)controller->Close();web.Reset();controller.Reset();if(job){CloseHandle(job);job=nullptr;}if(backend){CloseHandle(backend);backend=nullptr;}PostQuitMessage(0);return 0;
 }
 return DefWindowProcW(h,m,w,l);
}
int WINAPI wWinMain(HINSTANCE app,HINSTANCE,LPWSTR,int show){
 SetEnvironmentVariableW(L"PYTHONUTF8",L"1");
 SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
 PWSTR local=nullptr;SHGetKnownFolderPath(FOLDERID_LocalAppData,0,nullptr,&local);dataRoot=fs::path(local?local:L".")/(std::wstring(channel)==L"preview"?L"DailyStudy Preview":L"DailyStudy");CoTaskMemFree(local);
 int argc=0;LPWSTR* argv=CommandLineToArgvW(GetCommandLineW(),&argc);for(int i=1;i+1<argc;i++)if(std::wstring(argv[i])==L"--data-dir")dataRoot=argv[++i];LocalFree(argv);
 std::wstring mutex=L"Local\\DailyStudy-"+std::to_wstring(std::hash<std::wstring>{}(dataRoot.wstring()));instance=CreateMutexW(nullptr,FALSE,mutex.c_str());
 if(GetLastError()==ERROR_ALREADY_EXISTS){MessageBoxW(nullptr,L"应用已经打开，请切换到已有学习窗口。",title,MB_OK);return 0;}
 WNDCLASSW wc{};wc.lpfnWndProc=WindowProc;wc.hInstance=app;wc.lpszClassName=L"DailyStudyWindow";wc.hCursor=LoadCursor(nullptr,IDC_ARROW);wc.hbrBackground=reinterpret_cast<HBRUSH>(COLOR_WINDOW+1);RegisterClassW(&wc);
 windowHandle=CreateWindowExW(0,wc.lpszClassName,title,WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,1280,840,nullptr,nullptr,app,nullptr);
 ShowWindow(windowHandle,show);UpdateWindow(windowHandle);startBackend();MSG msg{};while(GetMessageW(&msg,nullptr,0,0)>0){TranslateMessage(&msg);DispatchMessageW(&msg);}
 if(instance)CloseHandle(instance);CoUninitialize();return 0;
}
