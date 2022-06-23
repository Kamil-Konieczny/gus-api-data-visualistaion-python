from flask import Flask, render_template, url_for, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
import requests
from flask import request

app = Flask(__name__)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


class RegisterForm(FlaskForm):
    username = StringField(validators=[
        InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
        InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                'That username already exists. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(validators=[
        InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
        InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')


class ApiData(FlaskForm):
    def getData(fromYear, toYear, idZmienna, idPrzekroj):
        testPeroidAndPrice = []
        testPeroidsCodes = [270, 271, 272, 273]
        for years in range(fromYear,toYear+1):
            for peroids in testPeroidsCodes:
                URL = "https://api-dbw.stat.gov.pl/api/1.1.0/variable/variable-data-section?id-zmienna="+str(idZmienna)+"&id-przekroj="+str(idPrzekroj)+"&id-rok=" + \
                str(years) + "&id-okres=" + str(peroids) + "&ile-na-stronie=50&numer-strony=0&lang=pl"
                string_json = requests.get(URL)

                json = string_json.json()
                data_object = json['data']
                countOfValuesDefferentThanZero = 0
                valueSum = 0
                for u in data_object:
                    valueSum += u["wartosc"]
                    year = u["id-daty"]
                    peroid = u["id-okres"]
                    if u["wartosc"] != 0: countOfValuesDefferentThanZero += 1

                testPeroidAndPrice.append({'date': str(peroid % 10 + 1) + "kw. " + str(year),
                                           'averagePrice': round(valueSum / countOfValuesDefferentThanZero)})
        return testPeroidAndPrice


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)




@app.route('/dashboard', methods =["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        fromYear = request.form['fromYear']
        toYear = request.form['toYear']
    else:
        fromYear = 2019
        toYear = 2021
    user = current_user.username

    dataForAveragePriceForM2 = ApiData.getData(int(fromYear), int(toYear), 309, 485)
    labelsForAveragePriceForM2 = []
    valuesForAveragePriceForM2 = []
    for x in dataForAveragePriceForM2:
        labelsForAveragePriceForM2.append(x["date"])
        valuesForAveragePriceForM2.append(x["averagePrice"])

    dataForMedianPriceForM2 = ApiData.getData(int(fromYear), int(toYear), 307, 485)
    labelsForMedianPriceForM2 = []
    valuesForMedianPriceForM2 = []
    for x in dataForMedianPriceForM2:
        labelsForMedianPriceForM2.append(x["date"])
        valuesForMedianPriceForM2.append(x["averagePrice"])

    dataForAveragePriceForFlat = ApiData.getData(int(fromYear), int(toYear), 308, 485)
    labelsForAveragePriceFlat = []
    valuesForAveragePriceFlat = []
    for x in dataForAveragePriceForFlat:
        labelsForAveragePriceFlat.append(x["date"])
        valuesForAveragePriceFlat.append(x["averagePrice"])

    dataForPriceFlatPointer = ApiData.getData(int(fromYear), int(toYear), 310, 484)
    labelsForAverageFlatPricesPointer = []
    valuesForAverageFlatPricesPointer = []
    for x in dataForPriceFlatPointer:
        labelsForAverageFlatPricesPointer.append(x["date"])
        valuesForAverageFlatPricesPointer.append(x["averagePrice"])

    return render_template('dashboard.html',
                           labelsForAveragePriceForM2=labelsForAveragePriceForM2,
                           valuesForAveragePriceForM2=valuesForAveragePriceForM2,
                           labelsForMedianPriceForM2=labelsForMedianPriceForM2,
                           valuesForMedianPriceForM2=valuesForMedianPriceForM2,
                           labelsForAveragePriceFlat=labelsForAveragePriceFlat,
                           valuesForAveragePriceFlat=valuesForAveragePriceFlat,
                           valuesForAverageFlatPricesPointer=valuesForAverageFlatPricesPointer,
                           labelsForAverageFlatPricesPointer=labelsForAverageFlatPricesPointer,
                           user=user)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


if __name__ == "__main__":
    app.run(debug=True)
