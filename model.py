# Criação das tabelas
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flask_bcrypt import Bcrypt

app = Flask(__name__)

# Inicialização do Bcrypt
bcrypt = Bcrypt(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:admin@localhost/restaurante'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Cliente(db.Model):
    id_cliente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(11), nullable=False)
    senha_hash = db.Column(db.String(60), nullable=False)

    # Definição de senha com hashing
    def set_senha(self, senha):
        self.senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

    # Verificar a senha com hashing
    def check_senha(self, senha_digitada):
        return bcrypt.check_password_hash(self.senha_hash, senha_digitada)

class Restaurante(db.Model):
    id_restaurante = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
