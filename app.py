from flask import Flask, jsonify, request, make_response, redirect, render_template, g
from flask_jwt_extended import (
    create_access_token, get_jwt_identity, jwt_required,
    set_access_cookies, unset_jwt_cookies, JWTManager
)
import pymysql
import pymysql.cursors
from datetime import datetime, timedelta

# ----------------------------
# Flask app & secrets
# ----------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "flask@123"

# ----------------------------
# JWT (cookies mode)
# ----------------------------
app.config["JWT_SECRET_KEY"] = "sua_chave_secreta_aqui"   # troque em produção
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = False                   # True se HTTPS
app.config["JWT_ACCESS_COOKIE_PATH"] = "/"
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False             # habilite True em prod
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
jwt = JWTManager(app)

# ----------------------------
# Database (PyMySQL)
# ----------------------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin',
    'database': 'restaurante',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(**DB_CONFIG)
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ----------------------------
# Helpers (inputs e senha)
# ----------------------------
def get_field(name: str):
    """Aceita JSON ou x-www-form-urlencoded."""
    if request.is_json:
        data = request.get_json(silent=True) or {}
        return data.get(name)
    return request.form.get(name)

def hash_password(s: str) -> str:
    # Compatível com o schema atual. Em produção: use hashing (werkzeug.security)
    return s

def check_password(plain: str, stored: str) -> bool:
    return hash_password(plain) == stored

# ----------------------------
# Esquema dinâmico (detectar coluna de senha)
# ----------------------------
def get_password_column():
    """
    Detecta se a tabela cliente possui 'senha_hash' ou 'senha'.
    Cacheia em g para não consultar toda hora.
    """
    if hasattr(g, "pwd_col") and g.pwd_col:
        return g.pwd_col

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME='cliente'
              AND COLUMN_NAME IN ('senha_hash', 'senha')
            ORDER BY FIELD(COLUMN_NAME, 'senha_hash', 'senha')  -- prioriza senha_hash
            LIMIT 1
        """, (DB_CONFIG['database'],))
        row = cur.fetchone()
        if not row:
            raise RuntimeError(
                "Nenhuma coluna de senha encontrada em 'cliente'. "
                "Crie 'senha_hash' (recomendado) ou 'senha'."
            )
        g.pwd_col = row["COLUMN_NAME"]
        return g.pwd_col

# ----------------------------
# DB helpers (compatíveis com seu schema)
# ----------------------------
def fetch_user_by_email(email: str):
    """Retorna cliente por email (inclui senha como 'senha_guardada')."""
    pwd_col = get_password_column()
    conn = get_db()
    with conn.cursor() as cur:
        sql = f"""
            SELECT
                id_cliente,
                nome,
                email,
                telefone,
                {pwd_col} AS senha_guardada
            FROM cliente
            WHERE email=%s
            LIMIT 1
        """
        cur.execute(sql, (email,))
        return cur.fetchone()

def user_exists_by_id(user_id: int) -> bool:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM cliente WHERE id_cliente=%s) AS ok",
            (user_id,)
        )
        row = cur.fetchone()
        return bool(row and row["ok"])

def mesa_exists_by_id(id_mesa: int) -> bool:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS(SELECT 1 FROM mesa WHERE id_mesa=%s) AS ok",
            (id_mesa,)
        )
        row = cur.fetchone()
        return bool(row and row["ok"])

# ----------------------------
# Rotas
# ----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = get_field("email")
        senha = get_field("senha")

        if not email or not senha:
            return jsonify({"msg": "E-mail e senha são obrigatórios"}), 400

        try:
            usuario = fetch_user_by_email(email)
            if not usuario:
                return jsonify({"msg": "E-mail ou senha incorretos"}), 401

            if not check_password(senha, usuario["senha_guardada"]):
                return jsonify({"msg": "E-mail ou senha incorretos"}), 401

            access_token = create_access_token(identity=str(usuario["id_cliente"]))
            resp = make_response(redirect('/'))
            set_access_cookies(resp, access_token)
            return resp

        except Exception as e:
            print(f"Erro inesperado durante o login: {str(e)}")
            return jsonify({"msg": f"Erro interno no servidor durante o login: {str(e)}"}), 500

    # GET: renderiza página (se estiver usando templates)
    return render_template("login.html")

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro_cliente():
    if request.method == 'POST':
        nome = get_field('nome')
        email = get_field('email')
        telefone = get_field('telefone')
        senha = get_field('senha')

        if not all([nome, email, telefone, senha]):
            return jsonify({"msg": "Todos os campos são obrigatórios"}), 400

        pwd_col = get_password_column()
        senha_to_store = hash_password(senha)

        conn = get_db()
        try:
            with conn.cursor() as cur:
                sql = f"INSERT INTO cliente (nome, email, telefone, {pwd_col}) VALUES (%s, %s, %s, %s)"
                cur.execute(sql, (nome, email, telefone, senha_to_store))
            conn.commit()
            return redirect("/login")
        except Exception as e:
            conn.rollback()
            return jsonify({"msg": f"Erro ao cadastrar: {str(e)}"}), 500

    return render_template('cadastro.html')

@app.route('/minhas-reservas', methods=['GET'])
def exibir_reservas_html():
    """Renderiza a página HTML para visualizar as reservas."""
    return render_template('reservas.html')

@app.route('/realizar-reserva', methods=['GET', 'POST'])
@jwt_required()
def reservar():
    # identity vem como string
    id_cliente = get_jwt_identity()
    try:
        id_cliente_int = int(id_cliente)
    except:
        return jsonify({"msg": "Token inválido"}), 401

    if request.method == "POST":
        id_mesa = get_field("numero_mesa")
        data_reserva_str = get_field("data_reserva")  # "YYYY-MM-DD"
        hora_inicial_str = get_field("hora_inicial")    # "HH:MM" ou "YYYY-MM-DD HH:MM"
        hora_final_str = get_field("hora_final")      # idem

        # validações básicas
        if not all([id_mesa, data_reserva_str, hora_inicial_str, hora_final_str]):
            return jsonify({"msg": "Campos obrigatórios: numero_mesa, data_reserva, hora_inicio, hora_final"}), 400

        try:
            id_mesa = int(id_mesa)
        except:
            return jsonify({"msg": "numero da mesa deve ser inteiro"}), 400

        if not mesa_exists_by_id(id_mesa):
            return jsonify({"msg": "Mesa não encontrada"}), 404
        if not user_exists_by_id(id_cliente_int):
            return jsonify({"msg": "Cliente não encontrado"}), 404

        # Constrói DATETIME a partir de date + "HH:MM" ou aceita "YYYY-MM-DD HH:MM"
        def parse_datetime(date_str, time_or_datetime_str):
            s = time_or_datetime_str.strip()
            if len(s) <= 5:  # "HH:MM"
                return datetime.strptime(f"{date_str} {s}", "%Y-%m-%d %H:%M")
            return datetime.strptime(s, "%Y-%m-%d %H:%M")

        try:
            dt_inicio = parse_datetime(data_reserva_str, hora_inicial_str)
            dt_final = parse_datetime(data_reserva_str, hora_final_str)
            data_reserva = datetime.strptime(data_reserva_str, "%Y-%m-%d").date()
            if dt_final <= dt_inicio:
                return jsonify({"msg": "hora_final deve ser após hora inicial"}), 400
        except ValueError:
            return jsonify({"msg": "Formato inválido de data/hora. Use 'YYYY-MM-DD' e 'HH:MM'."}), 400

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO reserva (id_cliente, id_mesa, data_reserva, hora_inicio, hora_final)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (id_cliente_int, id_mesa, data_reserva, dt_inicio, dt_final)
                )
            conn.commit()
            return redirect('/menu')

        except Exception as e:
            conn.rollback()
            return jsonify({"msg": f"Erro ao realizar reserva: {str(e)}"}), 500

    # GET: pode renderizar formulário, se existir
    return render_template("reservar.html")

@app.route('/visualizar-reserva', methods=['GET'])
@jwt_required()
def visualizar_reservas():
    """Lista reservas do cliente logado (JSON), com dados da mesa e restaurante."""
    id_cliente = get_jwt_identity()
    try:
        id_cliente_int = int(id_cliente)
    except:
        return jsonify({"msg": "Token inválido"}), 401

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    r.id_reserva,
                    r.data_reserva,
                    r.hora_inicio,
                    r.hora_final,
                    m.id_mesa,
                    m.numero_mesa,
                    m.capacidade,
                    t.id_restaurante,
                    t.nome AS restaurante_nome,
                    t.endereco AS restaurante_endereco,
                    t.telefone AS restaurante_telefone
                FROM reserva r
                JOIN mesa m ON m.id_mesa = r.id_mesa
                JOIN restaurante t ON t.id_restaurante = m.id_restaurante
                WHERE r.id_cliente = %s
                ORDER BY r.hora_inicio DESC
                """,
                (id_cliente_int,)
            )
            reservas = cur.fetchall()
            resp = jsonify(reservas)
        return resp
    except Exception as e:
        return jsonify({"msg": f"Erro ao listar reservas: {str(e)}"}), 500

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    resp = make_response(jsonify({"msg": "Logout efetuado"}), 200)
    unset_jwt_cookies(resp)
    return resp

# ----------------------------
# Páginas simples (opcionais)
# ----------------------------
@app.route('/', methods=['GET'])
def pagina_principal():
    return render_template("pagina_principal.html")

@app.route('/menu', methods=['GET'])
def menu():
    return render_template("menu.html")

if __name__ == '__main__':
    app.run(debug=True)
