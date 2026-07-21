// 静态 demo 部署(github.io)不要写死本地后端地址, 否则会强制非 demo 模式导致页面空白
if (!window.location.hostname.endsWith("github.io")) {
  window.FACTOR_LAB_API_HOST = "http://127.0.0.1:8012";
}
