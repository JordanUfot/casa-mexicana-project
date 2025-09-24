from flask import Flask, jsonify, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from flask_bcrypt import Bcrypt

# Inicilização do Flask
app = Flask(__name__)

# Configuração do JWT
app.config['JWT_SECRET_KEY'] = 'teste@123'
jwt = JWTManager(app)

# Configuração do banco de dados 
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:admin@localhost/restaurante'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Inicialização do Bcrypt
bcrypt = Bcrypt(app)

# Criação das tabelas
class Cliente(db.Model):
    id_cliente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(11), nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False) # Alterar nome do campo e tipo de dado para armazaenar a senha com hashing

# Definição de senha com hashing
def set_senha(self, senha):
    self.senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

# Verificar a senha com hashing
def check_senha(self, senha):
    return bcrypt.check_password_hash(self.senha_hash, senha)

class Restaurante(db.Model):
    id_restaurante = db.Column(db.Integer, primary_key =True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(11), nullable=False)
    capacidade_total = db.Column(db.Integer, nullable=False)

class Mesa(db.Model):
    id_mesa = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero_mesa = db.Column(db.Integer, nullable=False)
    capacidade = db.Column(db.Integer, nullable=False)
    id_restaurante = db.Column(db.Integer, db.ForeignKey('restaurante.id_restaurante'), nullable=False)

class Reserva(db.Model):
    id_reserva = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'), nullable=False)
    id_mesa = db.Column(db.Integer, db.ForeignKey('mesa.id_mesa'), nullable=False)
    data_reserva = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.DateTime, nullable=False)
    hora_final = db.Column(db.DateTime, nullable=False)

# Rota de cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro_cliente():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        senha = request.form['senha']
        senha_hashed = bcrypt.generate_password_hash(senha).decode('utf-8')

        novo_cliente = Cliente(nome=nome, email=email, telefone=telefone, senha_hash=senha_hashed)

        db.session.add(novo_cliente)
        db.session.commit()
        return jsonify({"msg": "Cadastro realizado com sucesso!"})
    
    return render_template('cadastro.html')

# Rota de login
@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email', None)
    senha = request.json.get('senha', None)

    cliente = Cliente.query.filter_by(email=email).first()

    if cliente and cliente.check_senha(senha):    
        access_token = create_access_token(identity=cliente.id_cliente)
        return jsonify(access_token=access_token)
    
    return jsonify({"msg": "e-mail ou senha incorretos"}), 401

# Rota página principal
@app.route('/', methods=['GET'])
def pagina_principal():
    return render_template("pagina_principal.html")

# Rota menu
@app.route('/menu', methods=['GET'])
@jwt_required()
def menu():
    current_user_id = get_jwt_identity()
    return jsonify({"msg":f" Seja bem-vindo ao menu, cliente {current_user_id}!"}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)