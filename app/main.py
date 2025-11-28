import asyncio
import ipaddress
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field, ValidationError

DATA_DIR = Path("/data")
LOG_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"
SSL_DIR = Path("/ssl")
TEMPLATE_DIR = Path(__file__).parent / "templates"
CONFIG_PATH = DATA_DIR / "squid.conf"
HTPASSWD_PATH = DATA_DIR / "users.htpasswd"
PID_FILE = Path("/run/squid.pid")
CA_CERT = SSL_DIR / "squid_ca.pem"
CA_KEY = SSL_DIR / "squid_ca.key"
OPTIONS_PATH = DATA_DIR / "options.json"

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
app = FastAPI(title="Squid Proxy Manager")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

app.mount("/static", StaticFiles(directory=str(TEMPLATE_DIR.parent / "static")), name="static")


def read_options() -> dict:
    if OPTIONS_PATH.exists():
        with OPTIONS_PATH.open() as f:
            return json.load(f)
    return {}


class Options(BaseModel):
    proxy_port: int = Field(default=3128, ge=1, le=65535)
    allowed_networks: List[str] = Field(default_factory=lambda: ["127.0.0.1/32"])
    enable_auth: bool = False
    enable_ssl_bump: bool = False
    cache_size_mb: int = Field(default=512, ge=16, le=10240)
    generate_ca_on_first_run: bool = False

    @classmethod
    def model_validate(cls, value, *args, **kwargs):  # type: ignore[override]
        opts = super().model_validate(value, *args, **kwargs)
        if not opts.allowed_networks:
            raise ValueError("At least one allowed network must be provided")
        for cidr in opts.allowed_networks:
            try:
                ipaddress.ip_network(cidr, strict=False)
            except ValueError as exc:
                raise ValueError(f"Invalid allowed network {cidr}: {exc}") from exc
        return opts

    @classmethod
    def from_file(cls) -> "Options":
        raw = read_options()
        try:
            opts = cls(**raw)
        except ValidationError as err:
            raise RuntimeError(f"Invalid options: {err}") from err
        return opts


@dataclass
class ServiceStatus:
    running: bool
    pid: Optional[int]
    uptime: Optional[str]
    proxy_port: int
    ssl_bump: bool
    user_count: int


class UserModel(BaseModel):
    username: str
    password: str


class LogQuery(BaseModel):
    file: str = Field(pattern="^(access|cache)\.log$")
    lines: int = Field(default=50, ge=1, le=500)


class UserDeleteRequest(BaseModel):
    username: str


async def ensure_directories() -> None:
    for path in (DATA_DIR, LOG_DIR, CACHE_DIR, SSL_DIR):
        path.mkdir(parents=True, exist_ok=True)
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)


def render_config(options: Options) -> str:
    template = env.get_template("squid.conf.j2")
    rendered = template.render(
        options=options,
        pid_file=str(PID_FILE),
        config_path=str(CONFIG_PATH),
        log_dir=str(LOG_DIR),
        cache_dir=str(CACHE_DIR),
        htpasswd=str(HTPASSWD_PATH),
        ca_cert=str(CA_CERT),
        ca_key=str(CA_KEY),
    )
    return rendered


def write_config(options: Options) -> None:
    CONFIG_PATH.write_text(render_config(options))


def init_cache(options: Options) -> None:
    if not (CACHE_DIR / "00").exists():
        subprocess.run([
            "squid",
            "-z",
            "-f",
            str(CONFIG_PATH),
        ], check=True)


def start_squid(options: Options) -> None:
    write_config(options)
    init_cache(options)
    subprocess.run([
        "squid",
        "-f",
        str(CONFIG_PATH),
        "-s",
        "-N",
        "-Y",
        "-C",
        "-d",
        "1",
    ], check=True)


def stop_squid() -> None:
    subprocess.run(["squid", "-k", "shutdown", "-f", str(CONFIG_PATH)], check=False)


def reload_squid(options: Options) -> None:
    write_config(options)
    subprocess.run(["squid", "-k", "reconfigure", "-f", str(CONFIG_PATH)], check=True)


def read_pid() -> Optional[int]:
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None


def service_status(options: Options) -> ServiceStatus:
    pid = read_pid()
    running = False
    uptime: Optional[str] = None
    if pid:
        try:
            stat = Path(f"/proc/{pid}/stat").read_text().split()
            start_ticks = int(stat[21])
            ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
            with Path("/proc/uptime").open() as f:
                uptime_seconds = float(f.read().split()[0])
            boot_time = datetime.now() - timedelta(seconds=uptime_seconds)
            started_at = boot_time + timedelta(seconds=start_ticks / ticks)
            uptime = str(datetime.now() - started_at)
            running = True
        except Exception:
            running = False
    user_count = 0
    if HTPASSWD_PATH.exists():
        with HTPASSWD_PATH.open() as f:
            user_count = sum(1 for _ in f)
    return ServiceStatus(
        running=running,
        pid=pid,
        uptime=uptime,
        proxy_port=options.proxy_port,
        ssl_bump=options.enable_ssl_bump,
        user_count=user_count,
    )


def ca_metadata() -> dict:
    if not CA_CERT.exists():
        raise HTTPException(status_code=404, detail="CA not generated")
    fingerprint = subprocess.check_output([
        "openssl",
        "x509",
        "-in",
        str(CA_CERT),
        "-fingerprint",
        "-noout",
    ]).decode().strip()
    expires = subprocess.check_output([
        "openssl",
        "x509",
        "-in",
        str(CA_CERT),
        "-enddate",
        "-noout",
    ]).decode().strip()
    return {"fingerprint": fingerprint, "expires": expires, "cert_path": str(CA_CERT)}


def generate_ca() -> dict:
    if not SSL_DIR.exists():
        SSL_DIR.mkdir(parents=True, exist_ok=True)
    for path in (CA_CERT, CA_KEY):
        if path.exists():
            backup = path.with_suffix(path.suffix + ".bak")
            shutil.copy(path, backup)
    subprocess.run([
        "openssl",
        "req",
        "-new",
        "-newkey",
        "rsa:4096",
        "-days",
        "3650",
        "-nodes",
        "-x509",
        "-subj",
        "/CN=Squid Proxy CA",
        "-keyout",
        str(CA_KEY),
        "-out",
        str(CA_CERT),
    ], check=True)
    os.chmod(CA_KEY, 0o600)
    return ca_metadata()


def ensure_ca(options: Options) -> None:
    if options.enable_ssl_bump and not (CA_CERT.exists() and CA_KEY.exists()):
        if options.generate_ca_on_first_run:
            generate_ca()
        else:
            raise RuntimeError("SSL bump enabled but CA files are missing")


def list_users() -> List[str]:
    if not HTPASSWD_PATH.exists():
        return []
    with HTPASSWD_PATH.open() as f:
        return [line.split(":", 1)[0] for line in f if line.strip()]


def add_or_update_user(user: UserModel) -> None:
    HTPASSWD_PATH.parent.mkdir(parents=True, exist_ok=True)
    args = ["htpasswd", "-b", str(HTPASSWD_PATH), user.username, user.password]
    if not HTPASSWD_PATH.exists():
        args.insert(1, "-c")
    subprocess.run(args, check=True)


def delete_user(username: str) -> bool:
    if not HTPASSWD_PATH.exists():
        return False
    result = subprocess.run(["htpasswd", "-D", str(HTPASSWD_PATH), username], check=False)
    if result.returncode == 0:
        if HTPASSWD_PATH.exists() and HTPASSWD_PATH.stat().st_size == 0:
            HTPASSWD_PATH.unlink()
        return True
    return False


async def bootstrap() -> None:
    await ensure_directories()
    options = Options.from_file()
    ensure_ca(options)
    write_config(options)


@app.get("/status", response_model=ServiceStatus)
def api_status():
    options = Options.from_file()
    return service_status(options)


@app.post("/start")
def api_start():
    options = Options.from_file()
    ensure_ca(options)
    start_squid(options)
    return service_status(options)


@app.post("/stop")
def api_stop():
    stop_squid()
    return {"stopped": True}


@app.post("/reload")
def api_reload():
    options = Options.from_file()
    reload_squid(options)
    return {"reloaded": True}


@app.post("/ca")
def api_generate_ca():
    return generate_ca()


@app.get("/ca", response_class=PlainTextResponse)
def api_download_ca():
    if not CA_CERT.exists():
        raise HTTPException(status_code=404, detail="CA not generated")
    return CA_CERT.read_text()


@app.get("/ca/info")
def api_ca_info():
    return ca_metadata()


@app.get("/logs")
def api_logs(file: str, lines: int = 50):
    query = LogQuery(file=file, lines=lines)
    log_path = LOG_DIR / query.file
    if not log_path.exists():
        return []
    content = log_path.read_text().splitlines()
    return content[-query.lines :]


@app.post("/users")
def api_users(users: List[UserModel]):
    # Replace credential set with provided list
    if not users:
        if HTPASSWD_PATH.exists():
            HTPASSWD_PATH.unlink()
        return {"users": 0}
    tmp_path = HTPASSWD_PATH.with_suffix(".tmp")
    for idx, user in enumerate(users):
        args = ["htpasswd", "-b", str(tmp_path), user.username, user.password]
        if idx == 0:
            args.insert(1, "-c")
        subprocess.run(args, check=True)
    tmp_path.replace(HTPASSWD_PATH)
    return {"users": len(users)}


@app.get("/users")
def api_list_users():
    return list_users()


@app.post("/users/add")
def api_add_user(user: UserModel):
    add_or_update_user(user)
    return {"user": user.username}


@app.post("/users/delete")
def api_delete_user(req: UserDeleteRequest):
    deleted = delete_user(req.username)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": req.username}


@app.post("/options")
def api_write_options(options: Options):
    ensure_ca(options)
    OPTIONS_PATH.write_text(options.model_dump_json(indent=2))
    reload_squid(options)
    return options


@app.get("/options")
def api_read_options():
    return Options.from_file()


@app.post("/restart")
def api_restart():
    options = Options.from_file()
    stop_squid()
    start_squid(options)
    return service_status(options)


@app.get("/", response_class=HTMLResponse)
def ui_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def parse_cli() -> str:
    if len(sys.argv) < 2:
        return "serve"
    return sys.argv[1]


async def serve() -> None:
    await ensure_directories()
    options = Options.from_file()
    ensure_ca(options)
    start_squid(options)
    config = {
        "host": "0.0.0.0",
        "port": 8099,
        "reload": False,
        "log_level": "info",
        "app": "main:app",
    }
    import uvicorn

    uvicorn.run(**config)


def main() -> None:
    command = parse_cli()
    if command == "bootstrap":
        asyncio.run(bootstrap())
    elif command == "serve":
        asyncio.run(serve())
    else:
        raise SystemExit(f"Unknown command {command}")


if __name__ == "__main__":
    main()
