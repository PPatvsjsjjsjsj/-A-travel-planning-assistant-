import argparse
import threading
import webbrowser

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="启动探山旅游规划")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--no-browser", action="store_true", help="启动服务但不自动打开前端页面")
    args = parser.parse_args()

    display_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"http://{display_host}:{args.port}"
    if not args.no_browser and not args.reload:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"探山已启动：{url}")
    uvicorn.run("app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
