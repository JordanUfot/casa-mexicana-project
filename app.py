from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager

app = Flask(__name__)

# Configuração do JWT
app.config['JWT_SECRET_KEY'] = 'teste@123'
jwt = JWTManager(app)

# Configuração do banco de dados 
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:admin@localhost/restaurante'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Criação das tabelas
class cliente(db.Model):
    id_cliente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(11), nullable=False)
    senha = db.Column(db.String(8), nullable=False)

class restaurante(db.Model):
    id_restaurante = db.Column(db.Integer, primary_key =True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(11), nullable=False)
    capacidade_total = db.Column(db.Integer, nullable=False)

class mesa(db.Model):
    id_mesa = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero_mesa = db.Column(db.Integer, nullable=False)
    capacidade = db.Column(db.Integer, nullable=False)
    id_restaurante = db.Column(db.Integer, db.ForeignKey('restaurante.id_restaurante'), nullable=False)

class reserva(db.Model):
    id_reserva = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'), nullable=False)
    id_mesa = db.Column(db.Integer, db.ForeignKey('mesa.id_mesa'), nullable=False)
    data_reserva = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.DateTime, nullable=False)
    hora_final = db.Column(db.DateTime, nullable=False)

# Rota de cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    return render_template('cadastro.html')

# Rota de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    usuario = request.json.get('usuario', None)
    senha = request.json.get('senha', None)
    if usuario != '' or senha != '':
        return jsonify({"msg": "usuário ou senha incorretos"}), 401
    
    access_token = create_access_token(identity=usuario)
    return jsonify(access_token=access_token)

# Rota protegida
@app.route('/protegido', methods=['GET'])
@jwt_required()
def protegido():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

if __name__ == '__main__':
    app.run(debug=True)