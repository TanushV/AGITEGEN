from __future__ import annotations
from pathlib import Path
from jinja2 import Template
from .utils import run_cmd, console
from .embed import embed_backend

RN_CMD      = ["npx","create-expo-app"]
FLUTTER_CMD = ["flutter","create"]
NEXT_CMD    = ["npx","create-next-app@latest"]

def scaffold_project(root: Path, framework:str, targets:list[str], backend:str):
    if framework=="rn":
        run_cmd(RN_CMD+[root.name], cwd=root.parent)
    elif framework=="flutter-web":
        run_cmd(FLUTTER_CMD+["--platform","web",root.name], cwd=root.parent)
    elif framework=="flutter-desktop":
        run_cmd(FLUTTER_CMD+["--platform","macos,windows,linux",root.name], cwd=root.parent)
    elif framework=="next":
        run_cmd(NEXT_CMD+[root.name,"--eslint"], cwd=root.parent)
    elif framework in {"", "none", "skip"}:
        # Allow cases where only backend scaffolding is desired (e.g., `agitegen add-backend`)
        pass
    else:
        console.print("[red]Unknown framework"); return

    # ------------------------------------------------------------------
    # Backend repository/adapter scaffolding
    # ------------------------------------------------------------------
    if backend != "none":
        backend_dir = root / "src" / "backend"
        backend_dir.mkdir(parents=True, exist_ok=True)

        # 1. abstract.ts – defines the contract every adapter must fulfil
        abstract_ts = Template(
            """export interface BackendAdapter {
  // Authentication
  signIn(email: string, password: string): Promise<any>;
  signOut(): Promise<void>;
  getCurrentUser(): Promise<any | null>;

  // Generic CRUD helpers (collection/table based)
  create<T>(collection: string, data: T): Promise<string>;      // returns new id
  read<T>(collection: string, id: string): Promise<T | null>;
  update<T>(collection: string, id: string, data: Partial<T>): Promise<void>;
  list<T>(collection: string, query?: any): Promise<T[]>;
  delete(collection: string, id: string): Promise<void>;
}
""")
        (backend_dir / "abstract.ts").write_text(abstract_ts.render())

        # 2. Supabase adapter template
        supabase_adapter_ts = Template(
            """import { createClient, SupabaseClient } from '@supabase/supabase-js';\nimport { BackendAdapter } from './abstract';\n\nexport class SupabaseAdapter implements BackendAdapter {\n  private client!: SupabaseClient;\n\n  constructor() {\n    const url  = process.env.NEXT_PUBLIC_SUPABASE_URL  || process.env.SUPABASE_URL || '';\n    const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON || '';\n    // Lazy init when credentials are available; during unit-tests values may be empty.\n    if (url && anon) {\n      this.client = createClient(url, anon);\n    }\n  }\n\n  /* ---------------- Authentication ---------------- */\n  async signIn(email: string, password: string) {\n    // TODO: Replace with real implementation\n    return { email };\n  }\n  async signOut() {/* TODO */}\n  async getCurrentUser() { return null; }\n\n  /* ---------------- CRUD ---------------- */\n  async create<T>(collection: string, data: T) { /* TODO */ return 'stub-id'; }\n  async read<T>(collection: string, id: string) { /* TODO */ return null; }\n  async update<T>(collection: string, id: string, data: Partial<T>) {/* TODO */}\n  async list<T>(collection: string, query: any = {}) { /* TODO */ return []; }\n  async delete(collection: string, id: string) {/* TODO */}\n}\n""")
        (backend_dir / "supabaseAdapter.ts").write_text(supabase_adapter_ts.render())

        # 3. Firebase adapter template
        firebase_adapter_ts = Template(
            """import { initializeApp } from 'firebase/app';\nimport { getAuth } from 'firebase/auth';\nimport { getFirestore, doc, setDoc, getDoc, updateDoc, collection, getDocs, deleteDoc } from 'firebase/firestore';\nimport { BackendAdapter } from './abstract';\n\nexport class FirebaseAdapter implements BackendAdapter {\n  private app;\n  private auth;\n  private db;\n\n  constructor() {\n    const firebaseConfig = {\n      apiKey: process.env.FIREBASE_API_KEY,\n      authDomain: process.env.FIREBASE_AUTH_DOMAIN,\n      projectId: process.env.FIREBASE_PROJECT_ID,\n    };\n    this.app  = initializeApp(firebaseConfig);\n    this.auth = getAuth(this.app);\n    this.db   = getFirestore(this.app);\n  }\n\n  /* ---------------- Authentication ---------------- */\n  async signIn(email: string, password: string) { /* TODO */ return { email }; }\n  async signOut() {/* TODO */}\n  async getCurrentUser() { return null; }\n\n  /* ---------------- CRUD ---------------- */\n  async create<T>(collectionName: string, data: T) {\n    const colRef = collection(this.db, collectionName);\n    // TODO: Proper addDoc, using addDoc would require import from 'firebase/firestore'; kept minimal stub\n    const id = Math.random().toString(36).substring(2);\n    await setDoc(doc(colRef, id), data as any);\n    return id;\n  }\n  async read<T>(collectionName: string, id: string) {\n    const docSnap = await getDoc(doc(this.db, collectionName, id));\n    return docSnap.exists() ? (docSnap.data() as T) : null;\n  }\n  async update<T>(collectionName: string, id: string, data: Partial<T>) {\n    await updateDoc(doc(this.db, collectionName, id), data as any);\n  }\n  async list<T>(collectionName: string) {\n    const snap = await getDocs(collection(this.db, collectionName));\n    return snap.docs.map((d) => d.data() as T);\n  }\n  async delete(collectionName: string, id: string) {\n    await deleteDoc(doc(this.db, collectionName, id));\n  }\n}\n""")
        (backend_dir / "firebaseAdapter.ts").write_text(firebase_adapter_ts.render())

        # 4. Factory to select adapter at runtime based on AIDERGEN_BACKEND env
        factory_ts = Template(
            """import { SupabaseAdapter } from './supabaseAdapter';\nimport { FirebaseAdapter } from './firebaseAdapter';\nimport type { BackendAdapter } from './abstract';\n\nexport function getBackend(): BackendAdapter {\n  const target = process.env.AIDERGEN_BACKEND === 'firebase' ? 'firebase' : 'supabase';\n  return target === 'firebase' ? new FirebaseAdapter() : new SupabaseAdapter();\n}\n\nexport const backend = getBackend();\n""")
        (backend_dir / "index.ts").write_text(factory_ts.render())

        # Embed docs useful for LLM context
        embed_backend(backend, ["auth", "user", "database"], root)

def install_backend_deps(root: Path, backend:str):
    # Install client SDK and CLI tools for the chosen backend
    if backend == "supabase":
        # supabase-js SDK + Supabase CLI
        run_cmd("npm i @supabase/supabase-js supabase --save-dev", cwd=root)
    elif backend == "firebase":
        # Firebase SDK + Firebase CLI
        run_cmd("npm i firebase firebase-tools --save-dev", cwd=root)
