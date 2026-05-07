# -*- coding: utf-8 -*-
"""
Gerenciador de Projetos — Morais Engenharia v2.0
Paleta clara alinhada ao site de vendas/controle interno.
Python 3.11 | Tkinter | PyMuPDF | Pillow
"""
import multiprocessing
multiprocessing.freeze_support()

import io, json, os, sys, hashlib, threading, time, shutil, subprocess
import uuid, math
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ── Imports opcionais ─────────────────────────────────────────────────────────
try:
    import fitz
    FITZ_OK = True
except ImportError:
    FITZ_OK = False

try:
    from PIL import Image, ImageTk, ImageDraw, ImageGrab
    # Força carregamento do módulo _imaging para garantir que está funcional
    Image.new("RGB", (1,1))
    PIL_OK = True
except Exception:
    PIL_OK = False

try:
    from plyer import notification as _plyer
    PLYER_OK = True
except Exception:
    PLYER_OK = False

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════
PASTA_RAIZ_DEFAULT = r"C:\Users\felip\OneDrive\MORAIS ENGENHARIA\PROJETO"
APP_DATA = ".app_data"
CFG_LOCAL = Path.home() / ".moraiseng_v2.json"

STATUS_LIST = [
    "EM ANDAMENTO",
    "AGUARDANDO CONFERÊNCIA",
    "CONFERIDO (FAZER CORREÇÕES)",
    "CONFERIDO (PROSSEGUIR)",
    "FINALIZADO",
]

STATUS_COR = {
    "EM ANDAMENTO":               "#295778",
    "AGUARDANDO CONFERÊNCIA":     "#c9a227",
    "CONFERIDO (FAZER CORREÇÕES)":"#c0392b",
    "CONFERIDO (PROSSEGUIR)":     "#2a9d5c",
    "FINALIZADO":                 "#7f8c8d",
}

DISC_PADRAO = ["ARQ", "BANCADAS", "ELÉTRICO", "ESTRUTURAL",
               "HIDROSSANITÁRIO", "QUANTITATIVO",
               "GERAL", "ESTUDO", "AJUSTES"]

# ── Paleta clara (site Morais) ─────────────────────────────────────────────────
C = {
    "bg":      "#f5f7fa",   # fundo geral — cinza muito claro
    "white":   "#ffffff",   # branco puro — cards, painéis
    "surface": "#eef1f6",   # surface levemente acinzentada
    "border":  "#d0dce8",   # bordas suaves
    "primary": "#295778",   # azul petróleo — cor principal do site
    "primary2":"#1e3f58",   # azul mais escuro — hover
    "accent":  "#c9a227",   # dourado — destaque
    "accent2": "#a87d10",   # dourado escuro
    "text":    "#1a2533",   # texto principal
    "text2":   "#5a7080",   # texto secundário
    "ok":      "#2a9d5c",   # verde
    "warn":    "#c9a227",   # amarelo
    "err":     "#c0392b",   # vermelho
    "link":    "#295778",   # azul link
}

F_TITLE = ("Segoe UI", 15, "bold")
F_HEAD  = ("Segoe UI", 11, "bold")
F_BODY  = ("Segoe UI", 10)
F_SMALL = ("Segoe UI", 9)

# ══════════════════════════════════════════════════════════════════════════════
# DATASTORE
# ══════════════════════════════════════════════════════════════════════════════
class DataStore:
    def __init__(self, raiz: str):
        self.raiz     = Path(raiz)
        self.app_data = self.raiz / APP_DATA
        self.app_data.mkdir(parents=True, exist_ok=True)
        self._fu = self.app_data / "users.json"
        self._ft = self.app_data / "tasks.json"
        self._fi = self.app_data / "chat_imgs"
        self._fi.mkdir(exist_ok=True)
        for f in [self._fu, self._ft]:
            if not f.exists():
                f.write_text("[]", encoding="utf-8")

    def _r(self, p):
        try: return json.loads(p.read_text(encoding="utf-8"))
        except: return []

    def _w(self, p, d):
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    # users
    def users(self): return self._r(self._fu)
    def save_users(self, u): self._w(self._fu, u)

    def criar_user(self, nome, email, senha, cargo=""):
        us = self.users()
        if any(u["email"].lower() == email.lower() for u in us):
            raise ValueError("Email já cadastrado.")
        u = {"id": str(uuid.uuid4()), "nome": nome, "email": email,
             "senha": hashlib.sha256(senha.encode()).hexdigest(),
             "cargo": cargo, "criado": datetime.now().isoformat()}
        us.append(u); self.save_users(us); return u

    def autenticar(self, email, senha):
        h = hashlib.sha256(senha.encode()).hexdigest()
        return next((u for u in self.users()
                     if u["email"].lower() == email.lower() and u["senha"] == h), None)

    # tasks
    def tasks(self): return self._r(self._ft)
    def save_tasks(self, t): self._w(self._ft, t)

    def get_task(self, tid):
        return next((t for t in self.tasks() if t["id"] == tid), None)

    def criar_task(self, titulo, pasta, disciplina, resp_id, prazo, autor_id):
        t = {"id": str(uuid.uuid4()), "titulo": titulo, "pasta": pasta,
             "disciplina": disciplina, "resp_id": resp_id, "prazo": prazo,
             "status": "EM ANDAMENTO", "autor_id": autor_id,
             "criado": datetime.now().isoformat(),
             "atualizado": datetime.now().isoformat(), "msgs": []}
        ts = self.tasks(); ts.append(t); self.save_tasks(ts); return t

    def update_task(self, tid, **kw):
        ts = self.tasks()
        for t in ts:
            if t["id"] == tid:
                t.update(kw); t["atualizado"] = datetime.now().isoformat(); break
        self.save_tasks(ts)

    def add_msg(self, tid, autor_id, texto, anexos=None):
        ts = self.tasks()
        for t in ts:
            if t["id"] == tid:
                t["msgs"].append({"id": str(uuid.uuid4()), "autor_id": autor_id,
                                  "texto": texto, "anexos": anexos or [],
                                  "ts": datetime.now().isoformat()})
                t["atualizado"] = datetime.now().isoformat(); break
        self.save_tasks(ts)

    def del_task(self, tid):
        ts = [t for t in self.tasks() if t["id"] != tid]
        self.save_tasks(ts)

    def salvar_img(self, pil_img):
        """Salva imagem PIL em chat_imgs e retorna o path string."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dest = self._fi / f"img_{ts}.png"
        pil_img.save(str(dest), "PNG")
        return str(dest)

    def msgs_novas(self, uid, janela_seg=300):
        agora = datetime.now()
        res = []
        for t in self.tasks():
            for m in t.get("msgs", []):
                if m["autor_id"] == uid: continue
                if (agora - datetime.fromisoformat(m["ts"])).total_seconds() < janela_seg:
                    res.append((t, m))
        return res

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS UI
# ══════════════════════════════════════════════════════════════════════════════
def setup_style():
    s = ttk.Style(); s.theme_use("clam")
    s.configure(".", background=C["bg"], foreground=C["text"], font=F_BODY)
    s.configure("TFrame", background=C["bg"])
    s.configure("White.TFrame", background=C["white"])

    s.configure("Treeview", background=C["white"], foreground=C["text"],
                fieldbackground=C["white"], rowheight=24, borderwidth=0)
    s.configure("Treeview.Heading", background=C["surface"],
                foreground=C["primary"], font=F_SMALL, borderwidth=0)
    s.map("Treeview", background=[("selected", C["primary"])],
          foreground=[("selected", "#ffffff")])

    s.configure("Vertical.TScrollbar", background=C["surface"],
                troughcolor=C["bg"], arrowcolor=C["text2"], borderwidth=0)
    s.map("Vertical.TScrollbar", background=[("active", C["primary"])])
    s.configure("Horizontal.TScrollbar", background=C["surface"],
                troughcolor=C["bg"], arrowcolor=C["text2"], borderwidth=0)

    s.configure("TNotebook", background=C["bg"], borderwidth=0)
    s.configure("TNotebook.Tab", background=C["surface"],
                foreground=C["text2"], padding=(14, 7), font=F_BODY)
    s.map("TNotebook.Tab",
          background=[("selected", C["white"])],
          foreground=[("selected", C["primary"])])

    s.configure("TCombobox", fieldbackground=C["white"], foreground=C["text"],
                background=C["white"], arrowcolor=C["primary"],
                selectbackground=C["surface"], selectforeground=C["text"])
    s.map("TCombobox",
          fieldbackground=[("readonly", C["white"])],
          foreground=[("readonly", C["text"])],
          selectbackground=[("readonly", C["surface"])],
          selectforeground=[("readonly", C["text"])])

def btn(parent, text, cmd, *, bg=None, fg=None, font=F_BODY, pad=(12,6), w=None):
    bg = bg or C["primary"]; fg = fg or "#ffffff"
    kw = dict(text=text, command=cmd, bg=bg, fg=fg, font=font,
              relief="flat", cursor="hand2", padx=pad[0], pady=pad[1],
              activebackground=C["primary2"] if bg == C["primary"] else bg,
              activeforeground=fg, bd=0)
    if w: kw["width"] = w
    return tk.Button(parent, **kw)

def lbl(parent, text, *, fg=None, font=F_BODY, bg=None, **kw):
    return tk.Label(parent, text=text, bg=bg or C["bg"],
                    fg=fg or C["text"], font=font, **kw)

def entry(parent, var=None, *, show=None, w=30, bg=None):
    kw = dict(bg=bg or C["white"], fg=C["text"], insertbackground=C["text"],
              relief="solid", bd=1, highlightthickness=1,
              highlightbackground=C["border"], highlightcolor=C["primary"],
              font=F_BODY, width=w)
    if show: kw["show"] = show
    if var:  kw["textvariable"] = var
    return tk.Entry(parent, **kw)

def sep(parent, orient="x", **kw):
    bg = kw.pop("bg", C["border"])
    if orient == "x":
        return tk.Frame(parent, bg=bg, height=1, **kw)
    return tk.Frame(parent, bg=bg, width=1, **kw)

def card_frame(parent, **kw):
    return tk.Frame(parent, bg=C["white"], bd=0,
                    highlightthickness=1, highlightbackground=C["border"], **kw)

def render_pdf_page(doc, page_idx, zoom=1.5):
    """Renderiza uma página PDF como PIL Image. Retorna None se falhar."""
    if not FITZ_OK or not PIL_OK: return None
    try:
        page = doc[page_idx]
        pix  = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return Image.open(io.BytesIO(pix.tobytes("png")))
    except Exception as e:
        print(f"render_pdf_page erro: {e}")
        return None

def abrir_arquivo(path):
    try: subprocess.Popen(["cmd", "/c", "start", "", str(path)])
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════
class LoginDlg(tk.Toplevel):
    def __init__(self, master, ds: DataStore, email_salvo=""):
        super().__init__(master)
        self.ds = ds; self.user = None
        self.title("Morais Engenharia — Acesso")
        self.configure(bg=C["white"]); self.resizable(False, False)
        self.grab_set(); self._build(email_salvo)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.update_idletasks()
        w, h = 420, 500
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+"
                      f"{(self.winfo_screenheight()-h)//2}")

    def _build(self, email_salvo):
        tk.Frame(self, bg=C["primary"], height=5).pack(fill="x")
        tk.Label(self, text="MORAIS ENGENHARIA", font=("Segoe UI",14,"bold"),
                 bg=C["white"], fg=C["primary"]).pack(pady=(24,4))
        tk.Label(self, text="Gerenciador de Projetos", font=F_SMALL,
                 bg=C["white"], fg=C["text2"]).pack()

        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True, padx=24, pady=16)
        fl = tk.Frame(nb, bg=C["white"])
        fc = tk.Frame(nb, bg=C["white"])
        nb.add(fl, text="  Entrar  "); nb.add(fc, text="  Cadastrar  ")
        self._login_tab(fl, email_salvo); self._cad_tab(fc)

    def _field(self, f, label, show=None):
        tk.Label(f, text=label, bg=C["white"], fg=C["text2"],
                 font=F_SMALL).pack(anchor="w", pady=(10,2))
        v = tk.StringVar(); entry(f, var=v, show=show, w=34).pack(fill="x"); return v

    def _login_tab(self, f, email_salvo):
        self.v_email  = self._field(f, "Email")
        self.v_senha  = self._field(f, "Senha", show="●")
        self.v_lembrar = tk.BooleanVar(value=bool(email_salvo))
        if email_salvo: self.v_email.set(email_salvo)
        tk.Checkbutton(f, text="Lembrar neste PC", variable=self.v_lembrar,
                       bg=C["white"], fg=C["text2"], font=F_SMALL,
                       selectcolor=C["surface"],
                       activebackground=C["white"]).pack(anchor="w", pady=(10,0))
        btn(f, "ENTRAR", self._entrar, pad=(0,10)).pack(fill="x", pady=(16,4))
        self.v_msg = tk.StringVar()
        tk.Label(f, textvariable=self.v_msg, bg=C["white"],
                 fg=C["err"], font=F_SMALL).pack()

    def _cad_tab(self, f):
        self.v_cnome  = self._field(f, "Nome completo")
        self.v_cemail = self._field(f, "Email")
        # Cargo como Combobox
        tk.Label(f, text="Cargo", bg=C["white"], fg=C["text2"],
                 font=F_SMALL).pack(anchor="w", pady=(10,2))
        self.v_ccargo = tk.StringVar()
        ttk.Combobox(f, textvariable=self.v_ccargo, width=34,
                     values=["ESTAGIÁRIO", "ENGENHEIRO",
                             "SUPERVISOR DE PROJETOS", "DIRETOR"],
                     state="readonly").pack(fill="x")
        self.v_csenha = self._field(f, "Senha", show="●")
        self.v_csenha2= self._field(f, "Confirmar senha", show="●")
        btn(f, "CRIAR CONTA", self._cadastrar, pad=(0,10)).pack(fill="x", pady=(16,4))
        self.v_cmsg = tk.StringVar()
        tk.Label(f, textvariable=self.v_cmsg, bg=C["white"],
                 fg=C["err"], font=F_SMALL).pack()

    def _entrar(self):
        u = self.ds.autenticar(self.v_email.get().strip(), self.v_senha.get())
        if u: u["_lembrar"] = self.v_lembrar.get(); self.user = u; self.destroy()
        else: self.v_msg.set("Email ou senha incorretos.")

    def _cadastrar(self):
        n, e = self.v_cnome.get().strip(), self.v_cemail.get().strip()
        s1, s2 = self.v_csenha.get(), self.v_csenha2.get()
        if not n or not e or not s1:
            self.v_cmsg.set("Preencha nome, email e senha."); return
        if s1 != s2:
            self.v_cmsg.set("Senhas não coincidem."); return
        try:
            u = self.ds.criar_user(n, e, s1, self.v_ccargo.get().strip())
            u["_lembrar"] = True; self.user = u; self.destroy()
        except ValueError as ex:
            self.v_cmsg.set(str(ex))

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — EXPLORADOR
# ══════════════════════════════════════════════════════════════════════════════
class ExploradorPage(tk.Frame):
    def __init__(self, master, ds: DataStore, user: dict):
        super().__init__(master, bg=C["bg"])
        self.ds = ds; self.user = user
        self._pdf_doc = None; self._pdf_page = 0; self._zoom = 1.0
        self._img_ref = None
        self._build()
        self.after(400, self._carregar_arvore)

    def _build(self):
        pw = tk.PanedWindow(self, orient="horizontal", bg=C["border"],
                            sashwidth=4, sashrelief="flat")
        pw.pack(fill="both", expand=True)
        left  = tk.Frame(pw, bg=C["bg"], width=420); pw.add(left, minsize=360)
        right = tk.Frame(pw, bg=C["white"]);          pw.add(right, minsize=400)
        self._build_left(left); self._build_right(right)

    # ── Esquerdo ──────────────────────────────────────────────────────────────
    def _build_left(self, f):
        # barra busca
        bar = tk.Frame(f, bg=C["white"], pady=8, padx=10,
                       highlightthickness=1, highlightbackground=C["border"])
        bar.pack(fill="x")
        tk.Label(bar, text="🔍", bg=C["white"], fg=C["text2"]).pack(side="left")
        self.v_busca = tk.StringVar()
        self._busca_after = None
        def _agendar_filtro(*_):
            if self._busca_after:
                self.after_cancel(self._busca_after)
            self._busca_after = self.after(400, self._filtrar)
        self.v_busca.trace_add("write", _agendar_filtro)
        entry(bar, var=self.v_busca, w=22, bg=C["white"]).pack(
            side="left", fill="x", expand=True, padx=(6,0))

        tb = tk.Frame(f, bg=C["bg"], pady=4, padx=8); tb.pack(fill="x")
        btn(tb, "⟳", self._carregar_arvore, bg=C["surface"], fg=C["text2"],
            font=F_SMALL, pad=(6,3)).pack(side="left", padx=(0,4))
        btn(tb, "📂 Explorer", self._abrir_explorer,
            bg=C["surface"], fg=C["text2"], font=F_SMALL, pad=(8,3)).pack(side="left")

        ft = tk.Frame(f, bg=C["bg"])
        ft.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.tree = ttk.Treeview(ft, show="tree", selectmode="browse")
        sb = ttk.Scrollbar(ft, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.tree.pack(side="left", fill="both", expand=True)

        self.tree.tag_configure("pasta",   foreground=C["primary"])
        self.tree.tag_configure("arquivo", foreground=C["text"])
        self.tree.tag_configure("pdf",     foreground=C["link"])

        self.tree.bind("<<TreeviewOpen>>",  self._on_expand)
        self.tree.bind("<Double-Button-1>", self._on_dbl)
        self.tree.bind("<Button-3>",        self._on_rclick)

    def _carregar_arvore(self):
        self.tree.delete(*self.tree.get_children())
        for item in sorted(self.ds.raiz.iterdir(), key=lambda p: p.name.lower()):
            if item.name == APP_DATA: continue
            if item.is_dir():
                iid = self.tree.insert("", "end", text=f"📁  {item.name}",
                                       values=[str(item)], tags=["pasta"])
                self.tree.insert(iid, "end", text="__ph__", values=["__ph__"])
        self.update_idletasks()

    def _on_expand(self, event):
        iid = self.tree.focus()
        ch  = self.tree.get_children(iid)
        if len(ch) == 1 and self.tree.item(ch[0], "values")[0] == "__ph__":
            self.tree.delete(ch[0])
            self._fill_children(iid, Path(self.tree.item(iid, "values")[0]))

    def _fill_children(self, iid, path):
        try:
            items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except: return
        for it in items:
            if it.name == APP_DATA: continue
            if it.is_dir():
                c = self.tree.insert(iid, "end", text=f"📁  {it.name}",
                                     values=[str(it)], tags=["pasta"])
                self.tree.insert(c, "end", text="__ph__", values=["__ph__"])
            else:
                ext = it.suffix.lower()
                ic  = {"pdf":"📕 PDF","rvt":"🏗 RVT","dwg":"📐 DWG","xlsx":"📊 XLS","xls":"📊 XLS","docx":"📝 DOC","doc":"📝 DOC","png":"🖼 PNG","jpg":"🖼 JPG","jpeg":"🖼 JPG","dwf":"📄 DWF","ifc":"📄 IFC","skp":"📄 SKP","mp4":"🎥 MP4","zip":"📦 ZIP"}.get(ext.lstrip("."), "📄")
                tg  = "pdf" if ext == ".pdf" else "arquivo"
                self.tree.insert(iid, "end", text=f"{ic}  {it.name}",
                                 values=[str(it)], tags=[tg])

    def _on_dbl(self, event):
        iid = self.tree.focus()
        if not iid: return
        vals = self.tree.item(iid, "values")
        if not vals or vals[0] == "__ph__": return
        p = Path(vals[0])
        if p.is_file():
            if p.suffix.lower() == ".pdf": self._abrir_pdf(p)
            else: abrir_arquivo(p)
        elif p.is_dir():
            if self.tree.item(iid, "open"):
                self.tree.item(iid, open=False)
            else:
                self.tree.item(iid, open=True)
                self._on_expand(event)

    def _on_rclick(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid: return
        self.tree.selection_set(iid)
        vals = self.tree.item(iid, "values")
        p = Path(vals[0]) if vals and vals[0] != "__ph__" else None
        if not p: return
        m = tk.Menu(self, tearoff=0, bg=C["white"], fg=C["text"],
                    font=F_SMALL, activebackground=C["surface"])
        m.add_command(label="Abrir", command=lambda: abrir_arquivo(p))
        if p.is_dir():
            m.add_command(label="Abrir no Explorer",
                          command=lambda: subprocess.Popen(["explorer", str(p)]))
            m.add_separator()
            m.add_command(label="✅ Criar tarefa aqui",
                          command=lambda: self._criar_tarefa_aqui(p))
        m.post(event.x_root, event.y_root)

    def _criar_tarefa_aqui(self, path):
        if hasattr(self, "_cb_tarefa"):
            self._cb_tarefa(str(path))

    def _abrir_explorer(self):
        iid = self.tree.focus()
        target = self.ds.raiz
        if iid:
            vals = self.tree.item(iid, "values")
            if vals and vals[0] != "__ph__":
                p = Path(vals[0])
                target = p if p.is_dir() else p.parent
        subprocess.Popen(["explorer", str(target)])

    def _filtrar(self):
        termo = self.v_busca.get().strip().lower()
        if not termo:
            self._carregar_arvore(); return
        self.tree.delete(*self.tree.get_children())
        iid_map = {}
        for path in sorted(self.ds.raiz.rglob("*")):
            if APP_DATA in path.parts: continue
            if termo not in path.name.lower(): continue
            partes = []
            p = path
            while p != self.ds.raiz:
                partes.insert(0, p); p = p.parent
            par_iid = ""
            for parte in partes:
                k = str(parte)
                if k not in iid_map:
                    if parte.is_dir():
                        lbl_txt = f"📁  {parte.name}"
                        if parte.parent.parent == self.ds.raiz:
                            lbl_txt = f"📁  {parte.name}  ({parte.parent.name})"
                        iid = self.tree.insert(par_iid, "end", text=lbl_txt,
                                               values=[k], tags=["pasta"])
                        if parte == path and termo in parte.name.lower():
                            self._fill_children_busca(iid, parte)
                    else:
                        ext = parte.suffix.lower()
                        ic  = {"pdf":"📕 PDF","rvt":"🏗 RVT","dwg":"📐 DWG","xlsx":"📊 XLS","xls":"📊 XLS","docx":"📝 DOC","doc":"📝 DOC","png":"🖼 PNG","jpg":"🖼 JPG","jpeg":"🖼 JPG","dwf":"📄 DWF","ifc":"📄 IFC","skp":"📄 SKP","mp4":"🎥 MP4","zip":"📦 ZIP"}.get(ext.lstrip("."), "📄")
                        tg  = "pdf" if ext == ".pdf" else "arquivo"
                        iid = self.tree.insert(par_iid, "end",
                                               text=f"{ic}  {parte.name}",
                                               values=[k], tags=[tg])
                    iid_map[k] = iid
                par_iid = iid_map[k]

    def _fill_children_busca(self, iid, path):
        try:
            for it in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                if it.name == APP_DATA: continue
                if it.is_dir():
                    c = self.tree.insert(iid, "end", text=f"📁  {it.name}",
                                         values=[str(it)], tags=["pasta"])
                    self._fill_children_busca(c, it)
                else:
                    ext = it.suffix.lower()
                    ic = {"pdf":"📕 PDF","rvt":"🏗 RVT","dwg":"📐 DWG","xlsx":"📊 XLS","xls":"📊 XLS","docx":"📝 DOC","doc":"📝 DOC","png":"🖼 PNG","jpg":"🖼 JPG","jpeg":"🖼 JPG","dwf":"📄 DWF","ifc":"📄 IFC","skp":"📄 SKP","mp4":"🎥 MP4","zip":"📦 ZIP"}.get(ext.lstrip("."), "📄")
                    tg = "pdf" if ext == ".pdf" else "arquivo"
                    self.tree.insert(iid, "end", text=f"{ic}  {it.name}",
                                     values=[str(it)], tags=[tg])
        except: pass

    # ── Direito — visualizador PDF ────────────────────────────────────────────
    def _build_right(self, f):
        tb = tk.Frame(f, bg=C["surface"], pady=6, padx=10,
                      highlightthickness=1, highlightbackground=C["border"])
        tb.pack(fill="x")
        tk.Label(tb, text="Visualizador de PDF", bg=C["surface"],
                 fg=C["text2"], font=F_SMALL).pack(side="left")

        ctrl = tk.Frame(tb, bg=C["surface"]); ctrl.pack(side="right")
        btn(ctrl, "−", self._zoom_out, bg=C["surface"], fg=C["text2"],
            font=F_BODY, pad=(6,2)).pack(side="left", padx=2)
        self.v_zoom = tk.StringVar(value="100%")
        tk.Label(ctrl, textvariable=self.v_zoom, bg=C["surface"],
                 fg=C["text2"], font=F_SMALL, width=5).pack(side="left")
        btn(ctrl, "+", self._zoom_in, bg=C["surface"], fg=C["text2"],
            font=F_BODY, pad=(6,2)).pack(side="left", padx=2)
        tk.Label(ctrl, text="  ", bg=C["surface"]).pack(side="left")
        btn(ctrl, "◀", self._pg_ant, bg=C["surface"], fg=C["text2"],
            font=F_BODY, pad=(6,2)).pack(side="left", padx=2)
        self.v_pg = tk.StringVar(value="–")
        tk.Label(ctrl, textvariable=self.v_pg, bg=C["surface"],
                 fg=C["text2"], font=F_SMALL, width=8).pack(side="left")
        btn(ctrl, "▶", self._pg_prox, bg=C["surface"], fg=C["text2"],
            font=F_BODY, pad=(6,2)).pack(side="left", padx=2)

        pf = tk.Frame(f, bg=C["white"]); pf.pack(fill="both", expand=True)
        self.cv = tk.Canvas(pf, bg=C["white"], highlightthickness=0)
        sbv = ttk.Scrollbar(pf, orient="vertical", command=self.cv.yview)
        sbh = ttk.Scrollbar(pf, orient="horizontal", command=self.cv.xview)
        self.cv.configure(yscrollcommand=sbv.set, xscrollcommand=sbh.set)
        sbv.pack(side="right", fill="y"); sbh.pack(side="bottom", fill="x")
        self.cv.pack(fill="both", expand=True)

        self.cv.bind("<MouseWheel>",
                     lambda e: self.cv.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.cv.bind("<Control-MouseWheel>",
                     lambda e: self._zoom_in() if e.delta > 0 else self._zoom_out())
        self.cv.bind("<ButtonPress-3>",  lambda e: self.cv.scan_mark(e.x, e.y))
        self.cv.bind("<B3-Motion>",      lambda e: self.cv.scan_dragto(e.x, e.y, gain=1))
        self.cv.create_text(300, 180,
                            text="Dê duplo clique em um PDF\npara visualizá-lo aqui",
                            fill=C["text2"], font=F_HEAD, justify="center")

    def _abrir_pdf(self, path):
        if not FITZ_OK:
            messagebox.showerror("Erro", "PyMuPDF não instalado.\npip install pymupdf")
            return
        try:
            if self._pdf_doc: self._pdf_doc.close()
        except: pass
        try:
            self._pdf_doc = fitz.open(str(path))
            self._pdf_page = 0; self._zoom = 1.0
            self._render_pdf()
        except Exception as e:
            messagebox.showerror("Erro ao abrir PDF", str(e))

    def _render_pdf(self):
        if not self._pdf_doc: return
        if not PIL_OK:
            self.cv.delete("all")
            self.cv.create_text(300, 200,
                text="Pillow não funcionou.\nRode: pip install pillow==10.4.0",
                fill=C["err"], font=("Segoe UI",11), justify="center")
            return
        img = render_pdf_page(self._pdf_doc, self._pdf_page, self._zoom * 1.5)
        if img is None:
            self.cv.delete("all")
            self.cv.create_text(300, 200,
                text="Erro ao renderizar PDF.",
                fill=C["err"], font=("Segoe UI",11), justify="center")
            return
        photo = ImageTk.PhotoImage(img)
        self._img_ref = photo
        self.cv.delete("all")
        self.cv.create_image(0, 0, anchor="nw", image=photo)
        self.cv.configure(scrollregion=(0, 0, img.width, img.height))
        total = len(self._pdf_doc)
        self.v_pg.set(f"{self._pdf_page+1} / {total}")
        self.v_zoom.set(f"{int(self._zoom*100)}%")

    def _pg_ant(self):
        if self._pdf_doc and self._pdf_page > 0:
            self._pdf_page -= 1; self._render_pdf()

    def _pg_prox(self):
        if self._pdf_doc and self._pdf_page < len(self._pdf_doc)-1:
            self._pdf_page += 1; self._render_pdf()

    def _zoom_in(self):
        self._zoom = min(4.0, self._zoom + 0.25); self._render_pdf()

    def _zoom_out(self):
        self._zoom = max(0.25, self._zoom - 0.25); self._render_pdf()

# ══════════════════════════════════════════════════════════════════════════════
# EDITOR DE ANOTAÇÕES PDF
# ══════════════════════════════════════════════════════════════════════════════
class AnotadorPDF(tk.Toplevel):
    TOOLS = ["Retângulo", "Seta", "Texto", "Caneta"]
    CORES = ["#e74c3c","#e67e22","#f1c40f","#2ecc71","#3498db","#9b59b6"]

    def __init__(self, master, pdf_path: Path, ds: DataStore,
                 task_id: str, autor_id: str, reload_cb=None):
        super().__init__(master)
        self.pdf_path  = pdf_path
        self.ds        = ds
        self.task_id   = task_id
        self.autor_id  = autor_id
        self.reload_cb = reload_cb
        self._anotacoes = []
        self._drag_start = None
        self._temp = None
        self._caneta_pts = []
        self._zoom = 1.5
        self._page = 0
        self._img_ref = None
        self._base_img = None
        self.v_tool = tk.StringVar(value="Retângulo")
        self.v_cor  = tk.StringVar(value="#e74c3c")

        self.title(f"Anotar — {pdf_path.name}")
        self.configure(bg=C["bg"])
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        if not FITZ_OK:
            messagebox.showerror("Erro", "PyMuPDF não instalado.")
            self.destroy(); return
        try:
            self._doc = fitz.open(str(pdf_path))
        except Exception as e:
            messagebox.showerror("Erro", str(e)); self.destroy(); return

        self._build()
        self.update_idletasks()
        # Maximiza sem wm_state que causa minimizar no Windows
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.update()
        self.after(400, self._render)

    def _build(self):
        # toolbar
        tb = tk.Frame(self, bg=C["surface"], pady=6, padx=10,
                      highlightthickness=1, highlightbackground=C["border"])
        tb.pack(fill="x")

        tk.Label(tb, text="Ferramenta:", bg=C["surface"], fg=C["text2"],
                 font=F_SMALL).pack(side="left")
        for t in self.TOOLS:
            tk.Radiobutton(tb, text=t, variable=self.v_tool, value=t,
                           bg=C["surface"], fg=C["text"],
                           selectcolor=C["primary"], font=F_SMALL,
                           activebackground=C["surface"]).pack(side="left", padx=4)

        tk.Label(tb, text="  Cor:", bg=C["surface"], fg=C["text2"],
                 font=F_SMALL).pack(side="left", padx=(8,0))
        for cor in self.CORES:
            tk.Button(tb, bg=cor, width=2, relief="flat", cursor="hand2",
                      command=lambda c=cor: self.v_cor.set(c)).pack(side="left", padx=2)

        tk.Label(tb, text="  Esp:", bg=C["surface"], fg=C["text2"],
                 font=F_SMALL).pack(side="left", padx=(8,0))
        self.v_esp = tk.IntVar(value=3)
        tk.Spinbox(tb, from_=1, to=12, textvariable=self.v_esp, width=3,
                   bg=C["white"], fg=C["text"]).pack(side="left")

        btn(tb, "↩ Desfazer", self._desfazer, bg=C["surface"], fg=C["text2"],
            font=F_SMALL, pad=(8,4)).pack(side="left", padx=(10,0))
        btn(tb, "🗑 Limpar", self._limpar, bg=C["surface"], fg=C["text2"],
            font=F_SMALL, pad=(8,4)).pack(side="left", padx=4)

        pg = tk.Frame(tb, bg=C["surface"]); pg.pack(side="right")
        btn(pg, "◀", self._pg_ant, bg=C["surface"], fg=C["text2"],
            font=F_BODY, pad=(6,2)).pack(side="left")
        self.v_pg = tk.StringVar(value="1/1")
        tk.Label(pg, textvariable=self.v_pg, bg=C["surface"],
                 fg=C["text2"], font=F_SMALL, width=6).pack(side="left")
        btn(pg, "▶", self._pg_prox, bg=C["surface"], fg=C["text2"],
            font=F_BODY, pad=(6,2)).pack(side="left")

        btn(tb, "💾 Salvar no chat", self._salvar,
            font=F_SMALL, pad=(12,4)).pack(side="right", padx=(0,8))

        # canvas
        fc = tk.Frame(self, bg=C["bg"]); fc.pack(fill="both", expand=True)
        self.cv = tk.Canvas(fc, bg="#c8d8e4", cursor="crosshair",
                            highlightthickness=0)
        sbv = ttk.Scrollbar(fc, orient="vertical", command=self.cv.yview)
        sbh = ttk.Scrollbar(fc, orient="horizontal", command=self.cv.xview)
        self.cv.configure(yscrollcommand=sbv.set, xscrollcommand=sbh.set)
        sbv.pack(side="right", fill="y"); sbh.pack(side="bottom", fill="x")
        self.cv.pack(fill="both", expand=True)

        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",       self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        # Scroll = zoom no editor
        self.cv.bind("<MouseWheel>",      self._scroll_zoom_editor)
        # Botão do meio = pan
        self.cv.bind("<ButtonPress-2>",   lambda e: self.cv.scan_mark(e.x, e.y))
        self.cv.bind("<B2-Motion>",       lambda e: self.cv.scan_dragto(e.x, e.y, gain=1))
        # Botão direito = menu exclusão ou pan
        self.cv.bind("<ButtonPress-3>",   self._rclick_canvas)
        self._pan_start = None

    def _render(self):
        if not PIL_OK:
            self.cv.delete("all")
            self.cv.create_text(300, 200,
                text="Pillow não funcionou.\nRode: pip install pillow==10.4.0",
                fill="red", font=("Segoe UI",12), justify="center")
            return
        img = render_pdf_page(self._doc, self._page, self._zoom)
        if img is None:
            self.cv.delete("all")
            self.cv.create_text(300, 200,
                text="Erro ao renderizar PDF.\nVerifique se pymupdf está instalado.",
                fill="red", font=("Segoe UI",12), justify="center")
            return
        self._base_img = img.copy()
        photo = ImageTk.PhotoImage(img)
        self._img_ref = photo
        self.cv.delete("all")
        self.cv.create_image(0, 0, anchor="nw", image=photo)
        self.cv.configure(scrollregion=(0, 0, img.width, img.height))
        self.v_pg.set(f"{self._page+1}/{len(self._doc)}")
        for an in self._anotacoes:
            if an["page"] == self._page: self._draw_an(an)

    def _xy(self, ex, ey):
        return int(self.cv.canvasx(ex)), int(self.cv.canvasy(ey))

    def _rclick_canvas(self, e):
        """Botão direito: menu de exclusão em anotações próximas, ou pan."""
        x, y = self._xy(e.x, e.y)
        hits = []
        for an in reversed(self._anotacoes):
            if an["page"] != self._page: continue
            t = an["type"]
            hit = False
            if t in ("rect","seta"):
                x0,y0,x1,y1 = an.get("x0",0),an.get("y0",0),an.get("x1",0),an.get("y1",0)
                hit = (min(x0,x1)-25 <= x <= max(x0,x1)+25 and
                       min(y0,y1)-25 <= y <= max(y0,y1)+25)
            elif t == "texto":
                hit = abs(x-an["x"]) < 100 and abs(y-an["y"]) < 40
            elif t == "caneta":
                hit = any(abs(x-p[0]) < 25 and abs(y-p[1]) < 25 for p in an["pts"])
            if hit: hits.append(an)

        if hits:
            m = tk.Menu(self, tearoff=0, bg="#ffffff", fg="#1a2533",
                        font=("Segoe UI",9),
                        activebackground=C["primary"], activeforeground="#ffffff")
            tipos = {"rect":"Retângulo","seta":"Seta","texto":"Texto","caneta":"Traço"}
            for an in hits:
                m.add_command(
                    label=f"🗑  Excluir {tipos.get(an['type'], an['type'])}",
                    command=lambda a=an: self._excluir_an(a))
            m.post(e.x_root, e.y_root)
        else:
            self.cv.scan_mark(e.x, e.y)
            self.cv.bind("<B3-Motion>",
                         lambda ev: self.cv.scan_dragto(ev.x, ev.y, gain=1))

    def _excluir_an(self, an):
        self._anotacoes.remove(an)
        self._render()

    def _scroll_zoom_editor(self, e):
        if e.delta > 0:
            self._zoom = min(4.0, self._zoom + 0.2)
        else:
            self._zoom = max(0.3, self._zoom - 0.2)
        self._render()

    def _press(self, e):
        if self.v_tool.get() == "Selecionar":
            self.cv.scan_mark(e.x, e.y); return
        x, y = self._xy(e.x, e.y)
        self._drag_start = (x, y)
        if self.v_tool.get() == "Caneta": self._caneta_pts = [(x, y)]

    def _drag(self, e):
        if self.v_tool.get() == "Selecionar":
            self.cv.scan_dragto(e.x, e.y, gain=1); return
        if not self._drag_start: return
        x, y = self._xy(e.x, e.y); x0, y0 = self._drag_start
        cor = self.v_cor.get(); esp = self.v_esp.get()
        if self._temp: self.cv.delete(self._temp); self._temp = None
        t = self.v_tool.get()
        if t == "Retângulo":
            self._temp = self.cv.create_rectangle(x0,y0,x,y, outline=cor, width=esp)
        elif t == "Seta":
            self._temp = self.cv.create_line(x0,y0,x,y, fill=cor, width=esp,
                                              arrow="last", arrowshape=(16,20,6))
        elif t == "Caneta":
            self._caneta_pts.append((x, y))
            if len(self._caneta_pts) >= 2:
                pts = [c for p in self._caneta_pts for c in p]
                self._temp = self.cv.create_line(*pts, fill=cor, width=esp, smooth=True)

    def _release(self, e):
        if self.v_tool.get() == "Selecionar": return
        if not self._drag_start: return
        x, y = self._xy(e.x, e.y); x0, y0 = self._drag_start
        cor = self.v_cor.get(); esp = self.v_esp.get()
        if self._temp: self.cv.delete(self._temp); self._temp = None
        t = self.v_tool.get()
        an = None
        if t == "Texto":
            txt = simpledialog.askstring("Texto", "Digite:", parent=self)
            if txt: an = {"type":"texto","page":self._page,"x":x0,"y":y0,
                          "text":txt,"cor":cor,"esp":esp}
        elif t == "Retângulo" and (abs(x-x0)>4 or abs(y-y0)>4):
            an = {"type":"rect","page":self._page,"x0":x0,"y0":y0,"x1":x,"y1":y,
                  "cor":cor,"esp":esp}
        elif t == "Seta" and (abs(x-x0)>4 or abs(y-y0)>4):
            an = {"type":"seta","page":self._page,"x0":x0,"y0":y0,"x1":x,"y1":y,
                  "cor":cor,"esp":esp}
        elif t == "Caneta" and len(self._caneta_pts) >= 2:
            an = {"type":"caneta","page":self._page,"pts":self._caneta_pts[:],
                  "cor":cor,"esp":esp}
        if an:
            self._anotacoes.append(an); self._draw_an(an)
        self._drag_start = None; self._caneta_pts = []

    def _draw_an(self, an):
        cor = an["cor"]; esp = an["esp"]; t = an["type"]
        if t == "rect":
            self.cv.create_rectangle(an["x0"],an["y0"],an["x1"],an["y1"],
                                     outline=cor, width=esp)
        elif t == "seta":
            self.cv.create_line(an["x0"],an["y0"],an["x1"],an["y1"],
                                fill=cor, width=esp, arrow="last", arrowshape=(16,20,6))
        elif t == "texto":
            self.cv.create_text(an["x"],an["y"], text=an["text"], fill=cor,
                                font=("Segoe UI", int(12*self._zoom)), anchor="nw")
        elif t == "caneta":
            pts = an["pts"]
            if len(pts) >= 2:
                self.cv.create_line(*[c for p in pts for c in p],
                                    fill=cor, width=esp, smooth=True)

    def _desfazer(self):
        page_ans = [a for a in self._anotacoes if a["page"] == self._page]
        if page_ans:
            self._anotacoes.remove(page_ans[-1]); self._render()

    def _limpar(self):
        self._anotacoes = [a for a in self._anotacoes if a["page"] != self._page]
        self._render()

    def _pg_ant(self):
        if self._page > 0: self._page -= 1; self._render()

    def _pg_prox(self):
        if self._page < len(self._doc)-1: self._page += 1; self._render()

    def _salvar(self):
        if self._base_img is None:
            messagebox.showerror("Erro", "PDF não carregado ainda. Aguarde.")
            return
        if not PIL_OK:
            messagebox.showerror("Erro", "Pillow com problema. Rode:\npip install pillow==10.4.0")
            return
        img  = self._base_img.copy()
        draw = ImageDraw.Draw(img)
        for an in [a for a in self._anotacoes if a["page"] == self._page]:
            cor = an["cor"]; esp = an["esp"]; t = an["type"]
            if t == "rect":
                for i in range(esp):
                    draw.rectangle([an["x0"]+i,an["y0"]+i,an["x1"]-i,an["y1"]-i],
                                   outline=cor)
            elif t == "seta":
                draw.line([an["x0"],an["y0"],an["x1"],an["y1"]], fill=cor, width=esp)
                dx = an["x1"]-an["x0"]; dy = an["y1"]-an["y0"]
                ang = math.atan2(dy, dx); L = 20
                for da in [0.4, -0.4]:
                    ex = int(an["x1"] - L*math.cos(ang+da))
                    ey = int(an["y1"] - L*math.sin(ang+da))
                    draw.line([an["x1"],an["y1"],ex,ey], fill=cor, width=esp)
            elif t == "texto":
                draw.text((an["x"],an["y"]), an["text"], fill=cor)
            elif t == "caneta":
                pts = an["pts"]
                for i in range(len(pts)-1):
                    draw.line([pts[i][0],pts[i][1],pts[i+1][0],pts[i+1][1]],
                              fill=cor, width=esp)
        path = self.ds.salvar_img(img)
        self.ds.add_msg(self.task_id, self.autor_id,
                        f"Anotação em {self.pdf_path.name}", [path])
        if self.reload_cb: self.reload_cb()
        self.destroy()

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — TAREFAS
# ══════════════════════════════════════════════════════════════════════════════
class TarefasPage(tk.Frame):
    def __init__(self, master, ds: DataStore, user: dict):
        super().__init__(master, bg=C["bg"])
        self.ds = ds; self.user = user
        self._img_refs = []  # evita GC
        self._build()
        self.after(300, self._carregar)

    def _build(self):
        pw = tk.PanedWindow(self, orient="horizontal", bg=C["border"],
                            sashwidth=4, sashrelief="flat")
        pw.pack(fill="both", expand=True)
        left  = tk.Frame(pw, bg=C["bg"], width=420); pw.add(left, minsize=360)
        right = tk.Frame(pw, bg=C["white"]);          pw.add(right, minsize=400)
        self._build_left(left)
        self.detalhe = right
        lbl(right, "Selecione ou crie uma tarefa",
            fg=C["text2"], font=F_HEAD, bg=C["white"]).pack(expand=True)

    # ── Lista ─────────────────────────────────────────────────────────────────
    def _build_left(self, f):
        hdr = tk.Frame(f, bg=C["bg"], pady=8, padx=10); hdr.pack(fill="x")
        lbl(hdr, "Tarefas", font=F_HEAD).pack(side="left")
        btn(hdr, "+ Nova", self._nova, font=F_SMALL, pad=(10,4)).pack(side="right")

        # filtros
        flt = tk.Frame(f, bg=C["bg"], padx=10, pady=2); flt.pack(fill="x")
        lbl(flt, "Status:", fg=C["text2"], font=F_SMALL).pack(side="left")
        self.v_fstatus = tk.StringVar(value="ATIVOS")
        cb1 = ttk.Combobox(flt, textvariable=self.v_fstatus,
                           values=["ATIVOS","TODOS"] + STATUS_LIST,
                           state="readonly", width=20)
        cb1.pack(side="left", padx=(6,0))
        cb1.bind("<<ComboboxSelected>>", lambda _: self._carregar())

        flt2 = tk.Frame(f, bg=C["bg"], padx=10, pady=2); flt2.pack(fill="x")
        lbl(flt2, "Usuário:", fg=C["text2"], font=F_SMALL).pack(side="left")
        self.v_fuser = tk.StringVar(value="TODOS")
        self.cb_user = ttk.Combobox(flt2, textvariable=self.v_fuser,
                                    values=["TODOS"], state="readonly", width=20)
        self.cb_user.pack(side="left", padx=(6,0))
        self.cb_user.bind("<<ComboboxSelected>>", lambda _: self._carregar())
        self.after(400, self._update_users_filtro)

        sep(f).pack(fill="x", padx=10, pady=4)

        # lista rolável
        lf = tk.Frame(f, bg=C["bg"]); lf.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.lista_cv = tk.Canvas(lf, bg=C["bg"], highlightthickness=0)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.lista_cv.yview)
        self.lista_cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.lista_cv.pack(side="left", fill="both", expand=True)
        self.lista_inner = tk.Frame(self.lista_cv, bg=C["bg"])
        self._lwin = self.lista_cv.create_window((0,0), window=self.lista_inner, anchor="nw")
        self.lista_inner.bind("<Configure>",
                              lambda e: self.lista_cv.configure(
                                  scrollregion=self.lista_cv.bbox("all")))
        self.lista_cv.bind("<Configure>",
                           lambda e: self.lista_cv.itemconfig(self._lwin, width=e.width))
        self.lista_cv.bind("<MouseWheel>",
                           lambda e: self.lista_cv.yview_scroll(
                               int(-1*(e.delta/120)), "units"))

    def _update_users_filtro(self):
        us = self.ds.users()
        self._umap = {u["nome"]: u["id"] for u in us}
        self.cb_user["values"] = ["TODOS"] + list(self._umap.keys())

    def _carregar(self):
        for w in self.lista_inner.winfo_children(): w.destroy()
        fs = self.v_fstatus.get(); fu = self.v_fuser.get()
        tasks = self.ds.tasks()
        users = {u["id"]: u for u in self.ds.users()}

        if fs == "ATIVOS":
            tasks = [t for t in tasks if t["status"] != "FINALIZADO"]
        elif fs not in ("TODOS", "ATIVOS"):
            tasks = [t for t in tasks if t["status"] == fs]

        if fu != "TODOS" and hasattr(self, "_umap"):
            uid = self._umap.get(fu)
            if uid:
                tasks = [t for t in tasks
                         if t.get("resp_id") == uid or t.get("autor_id") == uid]

        tasks.sort(key=lambda t: t.get("atualizado", ""), reverse=True)
        if not tasks:
            lbl(self.lista_inner, "Nenhuma tarefa.", fg=C["text2"],
                font=F_SMALL).pack(pady=30)
            return
        for t in tasks: self._card(t, users)

    def _card(self, task, users):
        cor = STATUS_COR.get(task["status"], C["text2"])
        resp = users.get(task.get("resp_id",""), {})
        f = card_frame(self.lista_inner, cursor="hand2"); f.pack(fill="x", pady=3, padx=2)
        tk.Frame(f, bg=cor, width=4).pack(side="left", fill="y")
        body = tk.Frame(f, bg=C["white"], padx=10, pady=8)
        body.pack(side="left", fill="both", expand=True)
        lbl(body, task["titulo"], font=F_HEAD, bg=C["white"]).pack(anchor="w")

        row = tk.Frame(body, bg=C["white"]); row.pack(fill="x", pady=(2,0))
        p = Path(task.get("pasta",""))
        obra = p.parent.name if p.parent != self.ds.raiz else p.name
        disc = task.get("disciplina","—")
        lbl(row, f"📁 {obra} › {disc}", fg=C["text2"], font=F_SMALL,
            bg=C["white"]).pack(side="left")

        row2 = tk.Frame(body, bg=C["white"]); row2.pack(fill="x", pady=(2,0))
        lbl(row2, task["status"], fg=cor, font=F_SMALL, bg=C["white"]).pack(side="left")
        if resp:
            lbl(row2, f"  •  {resp.get('nome','?')}", fg=C["text2"],
                font=F_SMALL, bg=C["white"]).pack(side="left")
        prazo = task.get("prazo","")
        if prazo:
            lbl(row2, f"  •  ⏰ {prazo[:10]}", fg=C["text2"],
                font=F_SMALL, bg=C["white"]).pack(side="left")

        all_w = [f, body] + list(body.winfo_children()) + \
                list(row.winfo_children()) + list(row2.winfo_children())
        for w in all_w:
            w.bind("<Button-1>", lambda e, tid=task["id"]: self._abrir(tid))
            w.bind("<Enter>",    lambda e, fw=f: fw.configure(highlightbackground=C["primary"]))
            w.bind("<Leave>",    lambda e, fw=f: fw.configure(highlightbackground=C["border"]))

    # ── Detalhe ───────────────────────────────────────────────────────────────
    def _abrir(self, tid):
        task = self.ds.get_task(tid)
        if not task: return
        for w in self.detalhe.winfo_children(): w.destroy()
        self._build_detalhe(task)

    def _build_detalhe(self, task):
        f = self.detalhe
        # scroll wrapper
        cv = tk.Canvas(f, bg=C["white"], highlightthickness=0)
        sb = ttk.Scrollbar(f, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); cv.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(cv, bg=C["white"])
        win   = cv.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",    lambda e: cv.itemconfig(win, width=e.width))

        def bind_scroll(w):
            w.bind("<MouseWheel>",
                   lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"))
            for c in w.winfo_children(): bind_scroll(c)

        inner.bind("<Configure>", lambda e, _cv=cv, _in=inner: (
            _cv.configure(scrollregion=_cv.bbox("all")), bind_scroll(_in)))

        pd = {"padx": 20, "pady": 6}
        users = {u["id"]: u for u in self.ds.users()}

        # título
        lbl(inner, task["titulo"], font=F_TITLE, bg=C["white"]).pack(fill="x", **pd)
        sep(inner, bg=C["border"]).pack(fill="x", padx=20, pady=2)

        # status
        rs = tk.Frame(inner, bg=C["white"]); rs.pack(fill="x", padx=20, pady=4)
        lbl(rs, "Status:", fg=C["text2"], font=F_SMALL, bg=C["white"]).pack(side="left")
        v_st = tk.StringVar(value=task["status"])
        ttk.Combobox(rs, textvariable=v_st, values=STATUS_LIST,
                     state="readonly", width=30).pack(side="left", padx=(8,0))
        lbl_ok = lbl(rs, "", fg=C["ok"], font=F_SMALL, bg=C["white"])
        lbl_ok.pack(side="left", padx=6)

        def salvar_status():
            self.ds.update_task(task["id"], status=v_st.get())
            self._carregar()
            lbl_ok.configure(text="✓ Salvo")
            self.after(2000, lambda: lbl_ok.configure(text=""))

        btn(rs, "Salvar", salvar_status, font=F_SMALL, pad=(8,3)).pack(side="left", padx=(6,0))

        # infos
        pasta = task.get("pasta","—")
        resp  = users.get(task.get("resp_id",""), {})

        def info(label, valor):
            r = tk.Frame(inner, bg=C["white"]); r.pack(fill="x", padx=20, pady=1)
            lbl(r, f"{label}:", fg=C["text2"], font=F_SMALL, bg=C["white"],
                width=12, anchor="w").pack(side="left")
            lbl(r, valor, fg=C["text"], font=F_SMALL, bg=C["white"],
                anchor="w").pack(side="left")

        info("Pasta",       pasta)
        info("Disciplina",  task.get("disciplina","—"))
        info("Responsável", resp.get("nome","—"))
        prazo_raw = task.get("prazo","")
        try:
            pp = prazo_raw.split("-")
            prazo_fmt = f"{pp[2]}/{pp[1]}/{pp[0]}" if len(pp)==3 else prazo_raw
        except: prazo_fmt = prazo_raw
        r_prazo = tk.Frame(inner, bg=C["white"]); r_prazo.pack(fill="x", padx=20, pady=1)
        lbl(r_prazo, "Prazo:", fg=C["text2"], font=F_SMALL, bg=C["white"],
            width=12, anchor="w").pack(side="left")
        v_prazo_edit = tk.StringVar(value=prazo_fmt)
        e_p = entry(r_prazo, var=v_prazo_edit, w=12, bg=C["white"])
        e_p.pack(side="left")
        def _fmt_p(*_):
            v = v_prazo_edit.get().replace("/","").replace("-","")
            v = "".join(c for c in v if c.isdigit())[:8]
            fmt = ""
            for i, c in enumerate(v):
                fmt += c
                if i in (1,3): fmt += "/"
            if fmt != v_prazo_edit.get():
                v_prazo_edit.set(fmt); e_p.icursor(len(fmt))
        v_prazo_edit.trace_add("write", _fmt_p)
        def _salvar_prazo():
            pv = v_prazo_edit.get().strip()
            try:
                pp2 = pv.split("/")
                iso = f"{pp2[2]}-{pp2[1]}-{pp2[0]}" if len(pp2)==3 else pv
            except: iso = pv
            self.ds.update_task(task["id"], prazo=iso)
            self._carregar()
            lbl_ok.configure(text="✓ Prazo salvo")
            self.after(2000, lambda: lbl_ok.configure(text=""))
        btn(r_prazo, "✓", _salvar_prazo, bg=C["surface"], fg=C["ok"],
            font=F_SMALL, pad=(6,2)).pack(side="left", padx=(4,0))
        info("Criado em",   task.get("criado","")[:16].replace("T"," "))

        # botões ação
        rb = tk.Frame(inner, bg=C["white"]); rb.pack(fill="x", padx=20, pady=8)

        def open_explorer():
            p = Path(pasta)
            subprocess.Popen(["explorer", str(p if p.is_dir() else p.parent)])

        def excluir_task():
            if messagebox.askyesno("Excluir", f"Excluir '{task['titulo']}'?"):
                self.ds.del_task(task["id"])
                self._carregar()
                for w in self.detalhe.winfo_children(): w.destroy()
                lbl(self.detalhe, "Selecione ou crie uma tarefa",
                    fg=C["text2"], font=F_HEAD, bg=C["white"]).pack(expand=True)

        def anotar_pdf():
            # Busca PDFs na pasta da tarefa
            p = Path(pasta)
            pdfs = sorted(p.rglob("*.pdf")) if p.is_dir() else \
                   [p] if p.suffix.lower() == ".pdf" else []
            if not pdfs:
                messagebox.showinfo("Sem PDF", "Nenhum PDF encontrado.")
                return
            if len(pdfs) == 1:
                pdf_sel = pdfs[0]
            else:
                dlg = tk.Toplevel(self); dlg.title("Selecionar PDF")
                dlg.configure(bg=C["white"]); dlg.grab_set()
                dlg.update_idletasks()
                w, h = 480, min(60 + len(pdfs)*36 + 20, 460)
                dlg.geometry(f"{w}x{h}+{(dlg.winfo_screenwidth()-w)//2}+"
                             f"{(dlg.winfo_screenheight()-h)//2}")
                lbl(dlg, "Selecione o PDF:", fg=C["text2"], font=F_SMALL,
                    bg=C["white"]).pack(padx=16, pady=(12,4), anchor="w")
                fl = tk.Frame(dlg, bg=C["white"]); fl.pack(fill="both", expand=True, padx=16)
                sb = ttk.Scrollbar(fl, orient="vertical")
                lb = tk.Listbox(fl, bg=C["white"], fg=C["text"], font=F_BODY,
                                selectbackground=C["primary"],
                                selectforeground="#ffffff",
                                relief="flat", yscrollcommand=sb.set)
                sb.config(command=lb.yview)
                sb.pack(side="right", fill="y"); lb.pack(side="left", fill="both", expand=True)
                for pdf in pdfs: lb.insert("end", f"  {pdf.name}")
                lb.selection_set(0)
                holder = [None]
                def confirmar(e=None):
                    idx = lb.curselection()
                    if idx: holder[0] = pdfs[idx[0]]
                    dlg.destroy()
                lb.bind("<Double-Button-1>", confirmar)
                btn(dlg, "Abrir →", confirmar, font=F_SMALL, pad=(16,6)).pack(pady=8)
                dlg.wait_window()
                if not holder[0]: return
                pdf_sel = holder[0]

            AnotadorPDF(self, pdf_sel, self.ds, task["id"], self.user["id"],
                        reload_cb=lambda: self._abrir(task["id"]))

        btn(rb, "📂 Abrir pasta", open_explorer,
            bg=C["surface"], fg=C["text2"], font=F_SMALL, pad=(10,4)).pack(side="left", padx=(0,6))
        btn(rb, "📌 Anotar PDF", anotar_pdf,
            bg=C["surface"], fg=C["link"], font=F_SMALL, pad=(10,4)).pack(side="left", padx=(0,6))
        btn(rb, "🗑 Excluir", excluir_task,
            bg="#fdf2f2", fg=C["err"], font=F_SMALL, pad=(10,4)).pack(side="left")

        sep(inner, bg=C["border"]).pack(fill="x", padx=20, pady=8)

        # chat
        lbl(inner, "Conversa", font=F_HEAD, bg=C["white"]).pack(anchor="w", padx=20)

        msgs_f = tk.Frame(inner, bg=C["surface"],
                          highlightthickness=1, highlightbackground=C["border"])
        msgs_f.pack(fill="x", padx=20, pady=(6,4))

        self._img_refs.clear()

        for msg in task.get("msgs", []):
            autor = users.get(msg["autor_id"], {})
            nome  = autor.get("nome", "?")
            ts    = msg["ts"][:16].replace("T"," ")
            eh_eu = msg["autor_id"] == self.user["id"]
            bg_mf = C["white"] if eh_eu else C["bg"]

            mf = tk.Frame(msgs_f, bg=bg_mf, padx=10, pady=8)
            mf.pack(fill="x", pady=1)

            hdr_m = tk.Frame(mf, bg=bg_mf); hdr_m.pack(fill="x")
            lbl(hdr_m, nome, fg=C["primary"], font=("Segoe UI",9,"bold"),
                bg=bg_mf).pack(side="left")
            lbl(hdr_m, f"  {ts}", fg=C["text2"], font=F_SMALL, bg=bg_mf).pack(side="left")

            if eh_eu:
                def _del_msg(mid=msg["id"]):
                    if messagebox.askyesno("Excluir", "Excluir mensagem?"):
                        t = self.ds.get_task(task["id"])
                        if t:
                            t["msgs"] = [m for m in t["msgs"] if m["id"] != mid]
                            ts2 = self.ds.tasks()
                            for i, tt in enumerate(ts2):
                                if tt["id"] == task["id"]: ts2[i] = t; break
                            self.ds.save_tasks(ts2)
                            self._abrir(task["id"])

                def _edit_msg(mid=msg["id"], txt=msg["texto"]):
                    novo = simpledialog.askstring("Editar", "Editar:", initialvalue=txt, parent=self)
                    if novo is not None:
                        t = self.ds.get_task(task["id"])
                        if t:
                            for m in t["msgs"]:
                                if m["id"] == mid: m["texto"] = novo; m["editado"] = True; break
                            ts2 = self.ds.tasks()
                            for i, tt in enumerate(ts2):
                                if tt["id"] == task["id"]: ts2[i] = t; break
                            self.ds.save_tasks(ts2)
                            self._abrir(task["id"])

                tk.Button(hdr_m, text="✏", command=_edit_msg, bg=bg_mf,
                          fg=C["text2"], font=F_SMALL, relief="flat",
                          cursor="hand2", padx=4).pack(side="right")
                tk.Button(hdr_m, text="🗑", command=_del_msg, bg=bg_mf,
                          fg=C["err"], font=F_SMALL, relief="flat",
                          cursor="hand2", padx=4).pack(side="right")

            editado = " (editado)" if msg.get("editado") else ""
            if msg["texto"]:
                lbl(mf, msg["texto"] + editado, fg=C["text"], font=F_SMALL,
                    bg=bg_mf, anchor="w", justify="left",
                    wraplength=520).pack(fill="x")

            # anexos
            for anx in msg.get("anexos", []):
                anx_p = Path(anx)
                ext   = anx_p.suffix.lower()
                # tenta variações de caminho
                found = next((p for p in [anx_p,
                              Path(str(anx_p).replace("/","\\")),
                              Path(str(anx_p).replace("\\","/"))]
                              if p.exists()), None)
                if ext in (".png",".jpg",".jpeg",".bmp",".gif") and PIL_OK:
                    if found:
                        try:
                            im = Image.open(str(found))
                            im.thumbnail((580, 440))
                            ph = ImageTk.PhotoImage(im)
                            self._img_refs.append(ph)
                            frm = tk.Frame(mf, bg=C["primary"], padx=2, pady=2,
                                           cursor="hand2")
                            frm.pack(anchor="w", pady=4)
                            li = tk.Label(frm, image=ph, bg=bg_mf, cursor="hand2")
                            li.pack()
                            for ww in [frm, li]:
                                ww.bind("<Button-1>",
                                        lambda e, p=found: abrir_arquivo(p))
                            lbl(mf, "  " + found.name, fg=C["text2"],
                                font=F_SMALL, bg=bg_mf).pack(anchor="w")
                        except Exception as ex:
                            lbl(mf, f"Erro ao exibir: {ex}", fg=C["err"],
                                font=F_SMALL, bg=bg_mf).pack(anchor="w")
                    else:
                        lbl(mf, f"⚠ Imagem não encontrada: {anx_p.name}",
                            fg=C["warn"], font=F_SMALL, bg=bg_mf).pack(anchor="w")
                else:
                    nome_anx = found.name if found else anx_p.name
                    tk.Button(mf, text=f"📎 {nome_anx}",
                              command=lambda p=found or anx_p: abrir_arquivo(p),
                              bg=C["surface"], fg=C["link"], font=F_SMALL,
                              relief="flat", cursor="hand2", anchor="w").pack(fill="x")

        # entrada
        ef = tk.Frame(inner, bg=C["white"], padx=20, pady=8); ef.pack(fill="x")

        self._anexos = []
        self._prev_ref = None

        prev_lbl = tk.Label(ef, bg=C["white"]); prev_lbl.pack(anchor="w")

        txt = tk.Text(ef, height=3, bg=C["white"], fg=C["text"],
                      insertbackground=C["text"], relief="solid", bd=1,
                      highlightthickness=1, highlightbackground=C["border"],
                      highlightcolor=C["primary"], font=F_BODY, wrap="word")
        txt.pack(fill="x")

        brow = tk.Frame(ef, bg=C["white"]); brow.pack(fill="x", pady=(6,0))
        lbl_anx = lbl(brow, "", fg=C["text2"], font=F_SMALL, bg=C["white"])

        def salvar_img_temp(img):
            return self.ds.salvar_img(img)

        def mostrar_prev(img):
            th = img.copy(); th.thumbnail((380, 180))
            ph = ImageTk.PhotoImage(th)
            self._prev_ref = ph; prev_lbl.configure(image=ph)

        def colar(event=None):
            if not PIL_OK: return
            try:
                im = ImageGrab.grabclipboard()
                if im is None: return
                if isinstance(im, list):
                    for pp in im:
                        pp = Path(pp)
                        if pp.suffix.lower() in (".png",".jpg",".jpeg",".bmp"):
                            im = Image.open(str(pp)); break
                    else: return
                dest = salvar_img_temp(im)
                self._anexos.append(dest)
                mostrar_prev(im)
                lbl_anx.configure(text=f"{len(self._anexos)} imagem(ns) colada(s)")
            except Exception as ex:
                lbl_anx.configure(text=f"Erro: {ex}")

        txt.bind("<Control-v>", colar); txt.bind("<Control-V>", colar)

        def on_enter(event):
            if event.state & 0x1: return  # Shift+Enter = quebra linha
            enviar(); return "break"
        txt.bind("<Return>", on_enter)

        def anexar():
            paths = filedialog.askopenfilenames(
                title="Selecionar arquivos",
                filetypes=[("Todos","*.*"),("PDF","*.pdf"),("Imagem","*.png *.jpg *.jpeg")])
            for pp in paths:
                pp = Path(pp); dest = self.ds.app_data / "chat_imgs" / pp.name
                self.ds.app_data.joinpath("chat_imgs").mkdir(exist_ok=True)
                shutil.copy2(str(pp), str(dest))
                self._anexos.append(str(dest))
                if pp.suffix.lower() in (".png",".jpg",".jpeg") and PIL_OK:
                    mostrar_prev(Image.open(str(pp)))
            if paths:
                lbl_anx.configure(text=f"{len(self._anexos)} arquivo(s) anexado(s)")

        def enviar():
            texto = txt.get("1.0","end").strip()
            if not texto and not self._anexos: return
            self.ds.add_msg(task["id"], self.user["id"], texto, self._anexos[:])
            self._anexos.clear(); prev_lbl.configure(image="")
            self._abrir(task["id"])

        lbl(ef, "💡 Ctrl+V para colar print | Shift+Enter para quebra de linha",
            fg=C["text2"], font=F_SMALL, bg=C["white"]).pack(anchor="w", pady=(4,0))

        btn(brow, "📎 Anexar", anexar,
            bg=C["surface"], fg=C["text2"], font=F_SMALL, pad=(8,4)).pack(side="left", padx=(0,6))
        lbl_anx.pack(side="left")
        btn(brow, "Enviar ▶", enviar, font=F_SMALL, pad=(12,4)).pack(side="right")

    # ── Nova tarefa ───────────────────────────────────────────────────────────
    def _nova(self, pasta_preenchida=None):
        NovaTarefaDlg(self, self.ds, self.user,
                      callback=self._carregar,
                      pasta_preenchida=pasta_preenchida)


class NovaTarefaDlg(tk.Toplevel):
    def __init__(self, master, ds: DataStore, user, callback=None, pasta_preenchida=None):
        super().__init__(master)
        self.ds = ds; self.user = user; self.callback = callback
        self.title("Nova Tarefa"); self.configure(bg=C["white"])
        self.resizable(False, False); self.grab_set()
        self._build(pasta_preenchida)
        self.update_idletasks()
        w, h = 500, 560
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+"
                      f"{(self.winfo_screenheight()-h)//2}")
        if pasta_preenchida: self._preencher_pasta(pasta_preenchida)

    def _field(self, f, label):
        tk.Label(f, text=label, bg=C["white"], fg=C["text2"],
                 font=F_SMALL).pack(anchor="w", pady=(10,2))
        v = tk.StringVar(); entry(f, var=v, w=48, bg=C["white"]).pack(fill="x"); return v

    def _build(self, pasta_pre):
        tk.Frame(self, bg=C["primary"], height=4).pack(fill="x")
        f = tk.Frame(self, bg=C["white"], padx=24, pady=16)
        f.pack(fill="both", expand=True)
        lbl(f, "Nova Tarefa", font=F_TITLE, fg=C["primary"], bg=C["white"]).pack(anchor="w", pady=(0,8))

        self.v_titulo = self._field(f, "Título *")

        # Obras dropdown
        tk.Label(f, text="Obra / Lote *", bg=C["white"], fg=C["text2"],
                 font=F_SMALL).pack(anchor="w", pady=(10,2))
        self._obras_map = {}
        for setor in sorted(self.ds.raiz.iterdir()):
            if not setor.is_dir() or setor.name == APP_DATA: continue
            for obra in sorted(setor.iterdir()):
                if obra.is_dir():
                    k = f"{setor.name}  ›  {obra.name}"
                    self._obras_map[k] = str(obra)

        self.v_obra = tk.StringVar()
        self.v_pasta = tk.StringVar()
        cb_obra = ttk.Combobox(f, textvariable=self.v_obra,
                               values=list(self._obras_map.keys()), width=46)
        cb_obra.pack(fill="x")
        cb_obra.bind("<<ComboboxSelected>>", lambda _: self._on_obra())
        cb_obra.bind("<KeyRelease>",
                     lambda e: cb_obra.configure(
                         values=[k for k in self._obras_map if cb_obra.get().lower() in k.lower()]))

        rp = tk.Frame(f, bg=C["white"]); rp.pack(fill="x", pady=(2,0))
        tk.Label(rp, text="ou pasta manual:", bg=C["white"],
                 fg=C["text2"], font=F_SMALL).pack(side="left")
        btn(rp, "…", self._manual_pasta, bg=C["surface"], fg=C["text2"],
            font=F_BODY, pad=(6,4)).pack(side="left", padx=(6,0))
        self.lbl_pasta = tk.Label(rp, text="", bg=C["white"], fg=C["text2"],
                                  font=F_SMALL, wraplength=280, anchor="w")
        self.lbl_pasta.pack(side="left", padx=(6,0))

        # disciplina
        tk.Label(f, text="Disciplina", bg=C["white"], fg=C["text2"],
                 font=F_SMALL).pack(anchor="w", pady=(10,2))
        self.v_disc = tk.StringVar()
        self.cb_disc = ttk.Combobox(f, textvariable=self.v_disc,
                                    values=DISC_PADRAO, width=46)
        self.cb_disc.pack(fill="x")
        # Editável: usuário pode digitar disciplina personalizada

        # responsável
        tk.Label(f, text="Responsável", bg=C["white"], fg=C["text2"],
                 font=F_SMALL).pack(anchor="w", pady=(10,2))
        us = self.ds.users()
        self._us = us
        nomes = [f"{u['nome']} <{u['email']}>" for u in us]
        self.v_resp = tk.StringVar()
        ttk.Combobox(f, textvariable=self.v_resp, values=nomes, width=46).pack(fill="x")

        # prazo
        tk.Label(f, text="Prazo (AAAA-MM-DD)", bg=C["white"], fg=C["text2"],
                 font=F_SMALL).pack(anchor="w", pady=(10,2))
        self.v_prazo = tk.StringVar()
        entry(f, var=self.v_prazo, w=20, bg=C["white"]).pack(anchor="w")

        self.v_err = tk.StringVar()
        tk.Label(f, textvariable=self.v_err, bg=C["white"],
                 fg=C["err"], font=F_SMALL).pack(pady=(8,0))
        btn(f, "CRIAR TAREFA", self._criar, pad=(0,10)).pack(fill="x", pady=(8,0))

    def _on_obra(self):
        sel = self.v_obra.get()
        if sel in self._obras_map:
            self.v_pasta.set(self._obras_map[sel])
            self._update_discs()

    def _manual_pasta(self):
        p = filedialog.askdirectory(initialdir=str(self.ds.raiz),
                                    title="Pasta do lote")
        if p:
            self.v_pasta.set(p)
            self.lbl_pasta.configure(text=Path(p).name)
            self._update_discs()

    def _update_discs(self):
        p = Path(self.v_pasta.get())
        discs = [d.name for d in sorted(p.iterdir()) if d.is_dir()] if p.exists() else []
        self.cb_disc["values"] = discs if discs else DISC_PADRAO

    def _preencher_pasta(self, pasta_str):
        self.v_pasta.set(pasta_str)
        p = Path(pasta_str)
        for k, v in self._obras_map.items():
            if v == pasta_str: self.v_obra.set(k); break
        self.lbl_pasta.configure(text=p.name)
        self._update_discs()

    def _criar(self):
        titulo = self.v_titulo.get().strip()
        pasta  = self.v_pasta.get().strip()
        if not titulo or not pasta:
            self.v_err.set("Título e pasta são obrigatórios."); return
        resp_id = None
        for u in self._us:
            if u["email"] in self.v_resp.get():
                resp_id = u["id"]; break
        self.ds.criar_task(titulo, pasta, self.v_disc.get(),
                           resp_id, self.v_prazo.get().strip(),
                           self.user["id"])
        if self.callback: self.callback()
        self.destroy()

# ══════════════════════════════════════════════════════════════════════════════
# JANELA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        setup_style()
        self.title("Gerenciador de Projetos — Morais Engenharia")
        self.configure(bg=C["bg"]); self.geometry("1300x820"); self.minsize(900,600)
        try:
            import os
            ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icone.ico")
            if os.path.exists(ico):
                self.iconbitmap(ico)
        except Exception:
            pass
        self.user = None; self.ds = None
        self._cfg = self._read_cfg()
        self.withdraw()
        self.after(100, self._init)

    def _read_cfg(self):
        try: return json.loads(CFG_LOCAL.read_text(encoding="utf-8"))
        except: return {}

    def _save_cfg(self):
        CFG_LOCAL.write_text(json.dumps(self._cfg, ensure_ascii=False, indent=2),
                             encoding="utf-8")

    def _init(self):
        pasta = self._cfg.get("pasta_raiz") or PASTA_RAIZ_DEFAULT
        if not Path(pasta).exists():
            # Tenta encontrar automaticamente em qualquer OneDrive do PC
            pasta = self._buscar_pasta_projeto()
        if not pasta or not Path(pasta).exists():
            pasta = filedialog.askdirectory(
                title="Selecione a pasta PROJETO no OneDrive",
                initialdir=str(Path.home()))
            if not pasta: self.destroy(); return
        self._cfg["pasta_raiz"] = pasta; self._save_cfg()

    def _buscar_pasta_projeto(self):
        """Busca automaticamente a pasta PROJETO em qualquer OneDrive do PC."""
        home = Path.home()
        # Candidatos comuns de pasta OneDrive
        candidatos = [
            home / "OneDrive" / "MORAIS ENGENHARIA" / "PROJETO",
            home / "OneDrive - Pessoal" / "MORAIS ENGENHARIA" / "PROJETO",
            home / "OneDrive - Morais Engenharia" / "MORAIS ENGENHARIA" / "PROJETO",
        ]
        # Busca também em subpastas do home chamadas OneDrive*
        for item in home.iterdir():
            if item.is_dir() and "onedrive" in item.name.lower():
                candidatos.append(item / "MORAIS ENGENHARIA" / "PROJETO")
        for c in candidatos:
            if c.exists():
                return str(c)
        return None

        self.ds = DataStore(pasta)

        # auto-login
        em  = self._cfg.get("lembrar_email","")
        sh  = self._cfg.get("lembrar_hash","")
        auto = None
        if em and sh:
            for u in self.ds.users():
                if u["email"].lower() == em.lower() and u["senha"] == sh:
                    auto = u; break

        if auto:
            self.user = auto
        else:
            dlg = LoginDlg(self, self.ds, em)
            self.wait_window(dlg)
            if not dlg.user: self.destroy(); return
            self.user = dlg.user
            if dlg.user.get("_lembrar"):
                self._cfg["lembrar_email"] = dlg.user["email"]
                self._cfg["lembrar_hash"]  = dlg.user["senha"]
            else:
                self._cfg.pop("lembrar_email",""); self._cfg.pop("lembrar_hash","")
            self._save_cfg()

        self.deiconify()
        self._build()
        self._start_notif()

    def _build(self):
        # topbar
        top = tk.Frame(self, bg=C["primary"], height=50)
        top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top, text="  MORAIS ENGENHARIA", font=("Segoe UI",13,"bold"),
                 bg=C["primary"], fg="#ffffff").pack(side="left", padx=(4,0))
        tk.Label(top, text="· Gerenciador de Projetos", font=F_BODY,
                 bg=C["primary"], fg="#aac8de").pack(side="left")
        tk.Label(top, text=f"👤  {self.user.get('nome','?')}", font=F_SMALL,
                 bg=C["primary"], fg="#aac8de").pack(side="right", padx=(0,16))
        self.v_notif = tk.StringVar()
        self.lbl_notif = tk.Label(top, textvariable=self.v_notif, font=F_SMALL,
                                  bg=C["err"], fg="white", padx=8)

        # navbar
        nav = tk.Frame(self, bg=C["white"],
                       highlightthickness=1, highlightbackground=C["border"])
        nav.pack(fill="x")

        container = tk.Frame(self, bg=C["bg"]); container.pack(fill="both", expand=True)
        self._pages = {}; self._nav_btns = {}

        def mk(nome, cls):
            p = cls(container, self.ds, self.user)
            self._pages[nome] = p; return p

        exp = mk("exp", ExploradorPage)
        tar = mk("tar", TarefasPage)

        # conectar "criar tarefa aqui"
        def cb_tarefa(pasta_str):
            show("tar"); tar._nova(pasta_preenchida=pasta_str)
        exp._cb_tarefa = cb_tarefa

        def show(nome):
            for n, p in self._pages.items(): p.pack_forget()
            self._pages[nome].pack(fill="both", expand=True)
            for n, b in self._nav_btns.items():
                ativo = n == nome
                b.configure(bg=C["primary"] if ativo else C["white"],
                            fg="#ffffff"    if ativo else C["text2"])

        for nome, label in [("exp","📁  Projetos"), ("tar","✅  Tarefas")]:
            b = tk.Button(nav, text=label, command=lambda n=nome: show(n),
                          bg=C["white"], fg=C["text2"], font=F_BODY,
                          relief="flat", padx=20, pady=10, bd=0,
                          cursor="hand2", activebackground=C["surface"],
                          activeforeground=C["primary"])
            b.pack(side="left"); self._nav_btns[nome] = b

        show("exp")
        self.after(800, self._checar_msgs_abertura)

    def _checar_msgs_abertura(self):
        """Ao abrir o app, mostra resumo de mensagens não lidas."""
        try:
            tasks   = self.ds.tasks()
            users   = {u["id"]: u for u in self.ds.users()}
            uid     = self.user["id"]
            resumo  = []  # (titulo_tarefa, qtd_msgs_novas)

            for t in tasks:
                # Só tarefas onde o usuário é autor ou responsável
                if t.get("autor_id") != uid and t.get("resp_id") != uid:
                    continue
                nao_lidas = [m for m in t.get("msgs", [])
                             if m["autor_id"] != uid]
                if nao_lidas:
                    resumo.append((t["titulo"], len(nao_lidas)))

            if not resumo:
                return  # sem mensagens, não mostra nada

            total = sum(q for _, q in resumo)

            # Monta janela de notificação
            dlg = tk.Toplevel(self)
            dlg.title("Mensagens não lidas")
            dlg.configure(bg=C["white"])
            dlg.resizable(False, False)
            dlg.grab_set()
            dlg.lift()
            dlg.focus_force()

            w, h = 400, min(120 + len(resumo) * 36, 480)
            dlg.geometry(f"{w}x{h}+{(dlg.winfo_screenwidth()-w)//2}+"
                         f"{(dlg.winfo_screenheight()-h)//2}")

            # Header colorido
            hdr = tk.Frame(dlg, bg=C["primary"], pady=12, padx=20)
            hdr.pack(fill="x")
            tk.Label(hdr, text=f"🔔  {total} mensagem(ns) não lida(s)",
                     font=("Segoe UI", 12, "bold"),
                     bg=C["primary"], fg="#ffffff").pack(anchor="w")

            # Lista de tarefas com msgs
            body = tk.Frame(dlg, bg=C["white"], padx=20, pady=10)
            body.pack(fill="both", expand=True)

            for titulo, qtd in resumo:
                row = tk.Frame(body, bg=C["surface"],
                               highlightthickness=1,
                               highlightbackground=C["border"])
                row.pack(fill="x", pady=3)
                tk.Frame(row, bg=C["accent"], width=4).pack(side="left", fill="y")
                inner = tk.Frame(row, bg=C["surface"], padx=10, pady=8)
                inner.pack(side="left", fill="both", expand=True)
                tk.Label(inner, text=titulo, font=("Segoe UI", 10, "bold"),
                         bg=C["surface"], fg=C["text"], anchor="w").pack(fill="x")
                tk.Label(inner, text=f"{qtd} mensagem(ns) nova(s)",
                         font=F_SMALL, bg=C["surface"],
                         fg=C["primary"], anchor="w").pack(fill="x")

            # Botão fechar
            btn_f = tk.Frame(dlg, bg=C["white"], pady=10)
            btn_f.pack(fill="x")
            def _ir_tarefas():
                dlg.destroy()
                for n, p in self._pages.items(): p.pack_forget()
                self._pages["tar"].pack(fill="both", expand=True)
                for n, b in self._nav_btns.items():
                    b.configure(bg=C["primary"] if n=="tar" else C["white"],
                                fg="#ffffff"    if n=="tar" else C["text2"])
            btn(btn_f, "Ver tarefas", _ir_tarefas,
                font=F_SMALL, pad=(14,6)).pack(side="right", padx=20)
            btn(btn_f, "Fechar", dlg.destroy,
                bg=C["surface"], fg=C["text2"],
                font=F_SMALL, pad=(14,6)).pack(side="right", padx=(0,6))

        except Exception as e:
            print(f"Erro ao checar msgs: {e}")

    def _start_notif(self):
        def loop():
            while True:
                try:
                    msgs = self.ds.msgs_novas(self.user["id"])
                    if msgs:
                        self.after(0, lambda n=len(msgs):
                                   self.v_notif.set(f"🔔 {n}"))
                        self.after(0, lambda: self.lbl_notif.pack(
                            side="right", padx=(0,8)))
                        if PLYER_OK:
                            t, m = msgs[0]
                            try:
                                _plyer.notify(
                                    title="Morais · Nova mensagem",
                                    message=f"{t['titulo']}: {m['texto'][:80]}",
                                    timeout=6)
                            except: pass
                    else:
                        self.after(0, lambda: self.v_notif.set(""))
                        self.after(0, lambda: self.lbl_notif.pack_forget())
                except: pass
                time.sleep(60)
        threading.Thread(target=loop, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    App().mainloop()
