from flask import Flask, render_template, request, redirect, url_for, session
from flask_pymongo import PyMongo
from flask_session import Session
from dotenv import load_dotenv
import os
import traceback
import re


load_dotenv()

app = Flask(__name__)


app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)


app.config['SECRET_KEY'] = 'your-secret-key-here-12345'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)



try:
    mongo.db.command("ping")
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    print(traceback.format_exc())

# Routes
@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    username_error = None
    password_error = None

    if request.method == 'POST':
        username = request.form.get('email')
        password = request.form.get('password')

        if not username or not password:
            if not username:
                username_error = "Username is required"
            if not password:
                password_error = "Password is required"
            return render_template('login.html', username_error=username_error, password_error=password_error), 400

        try:
            user = mongo.db.user1.find_one({"email": username})
            if not user:
                username_error = "The username doesn't exist"
                return render_template('login.html', username_error=username_error, password_error=password_error), 401

            if user["password"] != password:
                password_error = "Wrong password"
                return render_template('login.html', username_error=username_error, password_error=password_error), 401

            print(f"✅ Login success for {username}")

           
            session['user_email'] = username

           
            existing_meal_plan = mongo.db.meal_plan.find_one({"user_email": username})
            if existing_meal_plan:
                return redirect(url_for('display_meal_plan')) 

            return redirect(url_for('welcome'))

        except Exception as e:
            print(f"Login Error: {e}")
            print(traceback.format_exc())
            return render_template('login.html', username_error="Internal server error"), 500

    return render_template('login.html', username_error=None, password_error=None)

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    print("User logged out")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    password_error = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            if not password:
                password_error = "Password is required"
            return render_template('register.html', password_error=password_error), 400

        if '@' not in username:
            return render_template('register.html', password_error="Username must contain @"), 400

        if len(password) < 8 or not re.search(r'\d', password):
            password_error = "Password must be at least 8 characters and contain a number"
            return render_template('register.html', password_error=password_error), 400

        try:
            if mongo.db.user1.find_one({"email": username}):
                return render_template('register.html', password_error="Username already exists"), 400

            mongo.db.user1.insert_one({"email": username, "password": password})
            print(f"Registered new user: username={username}")
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error during registration: {e}")
            print(traceback.format_exc())
            return render_template('register.html', password_error="Failed to register user"), 500

    return render_template('register.html', password_error=None)

@app.route('/welcome')
def welcome():
    return render_template('webpage3.html')

@app.route('/bmi', methods=['GET', 'POST'])
def bmi():
    if request.method == 'POST':
        print("Received form data:", request.form)

        height = request.form.get('height')
        weight = request.form.get('weight')
        age = request.form.get('age')
        gender = request.form.get('gender')
        unit_preference = request.form.get('unit_preference')

        if not all([height, weight, age, gender, unit_preference]):
            missing_fields = [field for field in ['height', 'weight', 'age', 'gender', 'unit_preference'] if not request.form.get(field)]
            print(f"Missing fields: {missing_fields}")
            return f"All fields are required. Missing: {missing_fields}", 400

        try:
            height = float(height)
            weight = float(weight)
        except ValueError as e:
            print(f"Validation error: Height or weight not numeric - {e}")
            return "Height and weight must be numeric values", 400

        if unit_preference == 'metric':
            height_m = height / 100
            bmi = weight / (height_m ** 2)
        else:
            bmi = 703 * weight / (height ** 2)

        bmi = round(bmi, 2)

        if bmi < 18.5:
            category = "Underweight"
            diet_recommendation = "Focus on a nutrient-dense diet to gain healthy weight. Include high-calorie foods like nuts, avocados, and lean proteins."
        elif 18.5 <= bmi < 25:
            category = "Normal Weight"
            diet_recommendation = "Maintain your current diet with a balance of nutrients. Focus on whole foods, lean proteins, and regular exercise."
        elif 25 <= bmi < 30:
            category = "Overweight"
            diet_recommendation = "Focus on a calorie-controlled diet with more vegetables, lean proteins, and fewer processed foods. Incorporate regular physical activity."
        else:
            category = "Obese"
            diet_recommendation = "Focus on a low-calorie, balanced diet with portion control. Prioritize vegetables, lean proteins, and avoid sugary foods."

        try:
            result = mongo.db.bmi_data.insert_one({
                "height": height,
                "weight": weight,
                "age": age,
                "gender": gender,
                "unit_preference": unit_preference,
                "bmi": bmi,
                "category": category
            })
            print(f"Stored BMI data: height={height}, weight={weight}, age={age}, gender={gender}, unit_preference={unit_preference}, bmi={bmi}, category={category}, inserted_id={result.inserted_id}")
        except Exception as e:
            print(f"Error storing BMI data: {e}")
            print(traceback.format_exc())
            return "Failed to store BMI data", 500

        return redirect(url_for('bmi_results', bmi=bmi, category=category, diet_recommendation=diet_recommendation))

    return render_template('webpage4.html')

@app.route('/bmi_results')
def bmi_results():
    bmi = request.args.get('bmi', type=float)
    category = request.args.get('category')
    diet_recommendation = request.args.get('diet_recommendation')

    return render_template('webpage5.html', bmi=bmi, category=category, diet_recommendation=diet_recommendation)

@app.route('/meal_plan', methods=['GET', 'POST'])
def meal_plan():
    category = request.args.get('category')

    meal_plans = {
        "Underweight": {
            "Monday": [
                {"name": "Grilled Chicken with Rice", "image": "GrilledChickenRice.jpg", "alt": "Grilled chicken breast with a side of white rice and butter", "recipe": "1. Marinate 200g chicken breast with olive oil, garlic, salt, and pepper for 1 hour.\n2. Grill for 6-8 minutes per side.\n3. Cook 1 cup white rice with 2 tbsp butter and salt.\n4. Serve chicken with rice and a drizzle of olive oil.", "macros": {"calories": 600, "protein": 45, "carbs": 70, "fat": 20}},
                {"name": "Vegan Peanut Butter Bowl", "image": "peanutButterBowl.jpg", "alt": "A bowl of oats with peanut butter, banana, and chia seeds", "recipe": "1. Cook 1 cup oats with 2 cups almond milk.\n2. Stir in 2 tbsp peanut butter and 1 sliced banana.\n3. Add 1 tbsp chia seeds and a drizzle of maple syrup.\n4. Serve warm.", "macros": {"calories": 550, "protein": 18, "carbs": 75, "fat": 22}}
            ],
            "Tuesday": [
                {"name": "Salmon with Mashed Potatoes", "image": "salmonmashedpotatoes.jpg", "alt": "Baked salmon with creamy mashed potatoes and cream sauce", "recipe": "1. Bake 200g salmon with olive oil, lemon, and dill at 180°C for 20 minutes.\n2. Mash 2 boiled potatoes with 2 tbsp cream and butter.\n3. Serve salmon with mashed potatoes and a side of peas.", "macros": {"calories": 650, "protein": 40, "carbs": 50, "fat": 30}},
                {"name": "Vegan Lentil Curry", "image": "lentilcurry.jpg", "alt": "A rich lentil curry with coconut milk and spices", "recipe": "1. Sauté 1 onion and 2 garlic cloves in 2 tbsp coconut oil.\n2. Add 1 cup lentils, 1 can coconut milk, and 1 tbsp curry powder.\n3. Simmer for 25 minutes with diced tomatoes.\n4. Serve with 1 cup cooked rice.", "macros": {"calories": 600, "protein": 20, "carbs": 80, "fat": 25}}
            ],
            "Wednesday": [
                {"name": "Beef Stir-Fry with Noodles", "image": "Beefstirfry.jpg", "alt": "Beef stir-fry with noodles, bell peppers, and soy sauce", "recipe": "1. Stir-fry 200g beef strips with 2 tbsp soy sauce and garlic.\n2. Add bell peppers and cook for 5 minutes.\n3. Toss with 1 cup cooked noodles and sesame oil.\n4. Garnish with green onions.", "macros": {"calories": 700, "protein": 50, "carbs": 60, "fat": 25}},
                {"name": "Vegan Chickpea Stew", "image": "chickpeastew.jpg", "alt": "A hearty chickpea stew with sweet potatoes and spinach", "recipe": "1. Sauté 1 onion and 2 garlic cloves in 2 tbsp olive oil.\n2. Add 1 cup chickpeas, 1 diced sweet potato, and 2 cups vegetable broth.\n3. Simmer for 20 minutes, then add spinach.\n4. Season with salt and cumin.", "macros": {"calories": 550, "protein": 15, "carbs": 70, "fat": 18}}
            ],
            "Thursday": [
                {"name": "Pork Chops with Sweet Potato", "image": "pork.jpg", "alt": "Grilled pork chops with roasted sweet potato wedges", "recipe": "1. Grill 200g pork chops with salt, pepper, and paprika for 6-8 minutes per side.\n2. Roast 1 sweet potato (cut into wedges) with olive oil at 200°C for 25 minutes.\n3. Serve with a side of corn.", "macros": {"calories": 650, "protein": 45, "carbs": 50, "fat": 28}},
                {"name": "Vegan Avocado Toast", "image": "avacadotoast.jpg", "alt": "Whole grain toast topped with mashed avocado and seeds", "recipe": "1. Toast 2 slices of whole grain bread.\n2. Mash 1 avocado with lemon juice, salt, and pepper.\n3. Spread on toast and top with 1 tbsp sunflower seeds.\n4. Serve with a side of fruit.", "macros": {"calories": 500, "protein": 12, "carbs": 60, "fat": 22}}
            ],
            "Friday": [
                {"name": "Turkey with Pasta", "image": "turkeypasta.jpg", "alt": "Turkey slices with creamy pasta and parmesan", "recipe": "1. Cook 200g turkey breast with salt and herbs.\n2. Boil 1 cup pasta and mix with 2 tbsp cream sauce.\n3. Slice turkey and serve over pasta with parmesan.\n4. Add a side of broccoli.", "macros": {"calories": 700, "protein": 50, "carbs": 60, "fat": 25}},
                {"name": "Vegan Quinoa Stir-Fry", "image": "Quiona.jpg", "alt": "A quinoa stir-fry with tofu, peas, and soy sauce", "recipe": "1. Sauté 100g tofu cubes in 2 tbsp soy sauce.\n2. Add 1/2 cup cooked quinoa, peas, and carrots.\n3. Stir-fry for 5 minutes with garlic.\n4. Garnish with sesame seeds.", "macros": {"calories": 550, "protein": 20, "carbs": 70, "fat": 18}}
            ],
            "Saturday": [
                {"name": "Shrimp Fried Rice", "image": "shrimpFriedRice.jpg", "alt": "Fried rice with shrimp, peas, and scrambled egg", "recipe": "1. Cook 1 cup rice and set aside.\n2. Sauté 150g shrimp with 1 tsp oil and garlic.\n3. Add rice, peas, and 1 scrambled egg.\n4. Season with soy sauce and serve.", "macros": {"calories": 600, "protein": 35, "carbs": 70, "fat": 15}},
                {"name": "Vegan Nutty Bowl", "image": "nuttybowl.jpg", "alt": "A bowl with quinoa, nuts, and dried fruit", "recipe": "1. Cook 1/2 cup quinoa with 1 cup almond milk.\n2. Mix in 2 tbsp almonds, 1 tbsp raisins, and 1 tsp flaxseeds.\n4. Add a drizzle of agave syrup.\n5. Serve warm.", "macros": {"calories": 500, "protein": 15, "carbs": 65, "fat": 20}}
            ]
        },
        "Normal Weight": {
            "Monday": [
                {"name": "Grilled Chicken Salad", "image": "GrilledChicken.jpg", "alt": "A fresh salad with grilled chicken, mixed greens, and vinaigrette", "recipe": "1. Marinate 150g chicken breast with olive oil, lemon juice, garlic, salt, and pepper for 30 minutes.\n2. Grill for 5-7 minutes per side.\n3. Toss mixed greens with cherry tomatoes, cucumber, and red onion.\n4. Slice chicken and place on top, drizzle with 1 tbsp vinaigrette.", "macros": {"calories": 350, "protein": 30, "carbs": 15, "fat": 18}},
                {"name": "Quinoa Veggie Bowl", "image": "Quiona.jpg", "alt": "A colorful quinoa bowl with roasted vegetables and tahini", "recipe": "1. Cook 1/2 cup quinoa.\n2. Roast diced zucchini, bell peppers, and carrots with olive oil at 200°C for 20 minutes.\n3. Mix with quinoa and a handful of spinach.\n4. Drizzle with 1 tbsp tahini.", "macros": {"calories": 320, "protein": 12, "carbs": 45, "fat": 10}}
            ],
            "Tuesday": [
                {"name": "Salmon with Asparagus", "image": "salmon.jpg", "alt": "Grilled salmon fillet with roasted asparagus and lemon", "recipe": "1. Season 150g salmon with salt, pepper, and lemon zest.\n2. Grill for 4-5 minutes per side.\n3. Roast 10 asparagus spears with olive oil and garlic at 200°C for 15 minutes.\n4. Serve with a lemon wedge.", "macros": {"calories": 400, "protein": 35, "carbs": 5, "fat": 25}},
                {"name": "Chickpea Stir-Fry", "image": "chickpeaStirfry.jpg", "alt": "A vibrant stir-fry with chickpeas, bell peppers, and spinach", "recipe": "1. Sauté 1 cup chickpeas with 1 tsp olive oil, garlic, and cumin.\n2. Add bell peppers and spinach, stir-fry for 5-7 minutes.\n3. Season with salt and chili flakes.", "macros": {"calories": 300, "protein": 14, "carbs": 40, "fat": 8}}
            ],
            "Wednesday": [
                {"name": "Turkey Wrap", "image": "TurkeyWrap.jpg", "alt": "A whole wheat wrap with turkey, avocado, and veggies", "recipe": "1. Spread 1 tbsp hummus on a tortilla.\n2. Add 100g turkey, 1/4 avocado, lettuce, and tomato.\n3. Roll up and slice in half.\n4. Serve with cucumber sticks.", "macros": {"calories": 380, "protein": 28, "carbs": 35, "fat": 15}},
                {"name": "Lentil Soup", "image": "LentilSoup.jpg", "alt": "A warm bowl of lentil soup with carrots and herbs", "recipe": "1. Sauté 1 onion and 2 garlic cloves in 1 tsp olive oil.\n2. Add 1/2 cup lentils, 1 carrot, and 2 cups broth.\n3. Simmer for 20 minutes, season with cumin.", "macros": {"calories": 280, "protein": 18, "carbs": 40, "fat": 5}}
            ],
            "Thursday": [
                {"name": "Beef Stir-Fry", "image": "Beefstirfry.jpg", "alt": "Beef stir-fry with broccoli, bell peppers, and soy sauce", "recipe": "1. Marinate 150g beef with soy sauce and garlic.\n2. Stir-fry with broccoli and bell peppers for 5 minutes.\n3. Season with 1 tbsp soy sauce.", "macros": {"calories": 420, "protein": 38, "carbs": 20, "fat": 18}},
                {"name": "Vegetable Omelette", "image": "omelette.jpg", "alt": "A fluffy omelette with mushrooms, spinach, and tomatoes", "recipe": "1. Whisk 3 eggs with salt.\n2. Sauté mushrooms, spinach, and tomatoes.\n3. Pour eggs and cook for 3-4 minutes, fold and serve.", "macros": {"calories": 240, "protein": 20, "carbs": 8, "fat": 15}}
            ],
            "Friday": [
                {"name": "Shrimp Quinoa Salad", "image": "Quiona.jpg", "alt": "A quinoa salad with shrimp, cucumber, and feta", "recipe": "1. Cook 1/2 cup quinoa.\n2. Sauté 100g shrimp with garlic and lemon.\n3. Mix with cucumber, tomatoes, and 20g feta.\n4. Drizzle with 1 tbsp olive oil.", "macros": {"calories": 360, "protein": 25, "carbs": 35, "fat": 12}},
                {"name": "Stuffed Bell Peppers", "image": "StuffedBellPeppers.jpg", "alt": "Bell peppers stuffed with quinoa and black beans", "recipe": "1. Mix 1/2 cup quinoa with 1/2 cup black beans and tomatoes.\n2. Stuff 2 bell pepper halves.\n3. Bake at 180°C for 25 minutes.", "macros": {"calories": 310, "protein": 14, "carbs": 50, "fat": 6}}
            ],
            "Saturday": [
                {"name": "Chicken Avocado Wrap", "image": "ChickenWrap.jpg", "alt": "A wrap with grilled chicken, avocado, and lettuce", "recipe": "1. Grill 150g chicken with paprika.\n2. Spread yogurt on a tortilla, add chicken, avocado, and lettuce.\n3. Roll up and slice.", "macros": {"calories": 390, "protein": 30, "carbs": 35, "fat": 16}},
                {"name": "Sweet Potato Bowl", "image": "Sweetpotato.jpg", "alt": "A bowl with roasted sweet potato and kale", "recipe": "1. Roast 1 sweet potato with olive oil at 200°C for 25 minutes.\n2. Sauté kale with garlic.\n3. Mix and drizzle with 1 tbsp tahini.", "macros": {"calories": 340, "protein": 10, "carbs": 50, "fat": 12}}
            ]
        },
        "Overweight": {
            "Monday": [
                {"name": "Grilled Chicken with Veggies", "image": "GrilledChickenWithVeggies.jpg", "alt": "Grilled chicken with steamed broccoli and zucchini", "recipe": "1. Grill 120g chicken breast with salt and pepper.\n2. Steam 1 cup broccoli and 1 cup zucchini for 10 minutes.\n3. Serve with a squeeze of lemon.", "macros": {"calories": 250, "protein": 28, "carbs": 10, "fat": 8}},
                {"name": "Vegan Zucchini Noodles", "image": "ZucciniNoodles.jpg", "alt": "Zucchini noodles with tomato sauce and basil", "recipe": "1. Spiralize 2 zucchinis into noodles.\n2. Sauté with 1 cup low-sugar tomato sauce.\n3. Garnish with fresh basil.", "macros": {"calories": 150, "protein": 5, "carbs": 20, "fat": 5}}
            ],
            "Tuesday": [
                {"name": "Baked Cod with Spinach", "image": "BakedCod.jpg", "alt": "Baked cod fillet with wilted spinach and garlic", "recipe": "1. Bake 120g cod with lemon and pepper at 180°C for 15 minutes.\n2. Sauté 1 cup spinach with 1 tsp garlic.\n3. Serve together.", "macros": {"calories": 220, "protein": 30, "carbs": 5, "fat": 7}},
                {"name": "Vegan Lentil Salad", "image": "LentilSalad.jpg", "alt": "A light lentil salad with cucumber and lemon dressing", "recipe": "1. Mix 1/2 cup cooked lentils with diced cucumber.\n2. Add 1 tsp lemon juice and a pinch of salt.\n3. Serve cold.", "macros": {"calories": 180, "protein": 10, "carbs": 25, "fat": 2}}
            ],
            "Wednesday": [
                {"name": "Turkey Lettuce Wraps", "image": "Turkeylettuce.jpg", "alt": "Turkey wrapped in lettuce with a light sauce", "recipe": "1. Cook 100g ground turkey with garlic and spices.\n2. Wrap in large lettuce leaves with 1 tbsp salsa.\n3. Serve with a side of celery.", "macros": {"calories": 200, "protein": 25, "carbs": 5, "fat": 8}},
                {"name": "Vegan Cauliflower Rice", "image": "CauliflowerRice.jpg", "alt": "Cauliflower rice with turmeric and peas", "recipe": "1. Pulse 1 cauliflower head into rice-like pieces.\n2. Sauté with 1 tsp turmeric and 1/4 cup peas.\n3. Season with salt.", "macros": {"calories": 120, "protein": 5, "carbs": 15, "fat": 3}}
            ],
            "Thursday": [
                {"name": "Grilled Tuna with Greens", "image": "GrilledTuna.jpg", "alt": "Grilled tuna steak with mixed greens", "recipe": "1. Grill 120g tuna steak with pepper for 3-4 minutes per side.\n2. Serve over 1 cup mixed greens with 1 tsp olive oil.\n3. Add a squeeze of lime.", "macros": {"calories": 250, "protein": 35, "carbs": 3, "fat": 10}},
                {"name": "Vegan Broccoli Soup", "image": "BrocolliSoup.jpg", "alt": "A creamy broccoli soup without dairy", "recipe": "1. Blend 2 cups steamed broccoli with 1 cup vegetable broth.\n2. Season with salt, pepper, and a dash of nutmeg.\n3. Heat and serve.", "macros": {"calories": 150, "protein": 6, "carbs": 20, "fat": 4}}
            ],
            "Friday": [
                {"name": "Chicken Skewers", "image": "ChickenSkewers.jpg", "alt": "Chicken skewers with bell peppers and onions", "recipe": "1. Skewer 120g chicken with bell peppers and onions.\n2. Grill with salt and paprika for 8 minutes.\n3. Serve with a side of cucumber.", "macros": {"calories": 230, "protein": 30, "carbs": 8, "fat": 7}},
                {"name": "Vegan Spinach Stir-Fry", "image": "SpinachStirFry.jpg", "alt": "A stir-fry of spinach with mushrooms and soy sauce", "recipe": "1. Sauté 2 cups spinach with 1/2 cup mushrooms.\n2. Add 1 tsp soy sauce and garlic.\n3. Cook for 5 minutes.", "macros": {"calories": 100, "protein": 5, "carbs": 10, "fat": 3}}
            ],
            "Saturday": [
                {"name": "Baked Fish with Salad", "image": "Bakedfish.jpg", "alt": "Baked fish fillet with a fresh green salad", "recipe": "1. Bake 120g fish with lemon and herbs at 180°C for 15 minutes.\n2. Toss 1 cup salad greens with 1 tsp vinegar.\n3. Serve together.", "macros": {"calories": 200, "protein": 28, "carbs": 5, "fat": 6}},
                {"name": "Vegan Cucumber Soup", "image": "CucumberSoup.jpg", "alt": "A chilled cucumber soup with dill", "recipe": "1. Blend 2 cucumbers with 1 cup yogurt alternative.\n2. Add dill, salt, and a dash of lemon.\n3. Chill and serve.", "macros": {"calories": 120, "protein": 3, "carbs": 15, "fat": 4}}
            ]
        },
        "Obese": {
            "Monday": [
                {"name": "Steamed Chicken", "image": "steamedChicken.jpg", "alt": "Steamed chicken breast with herbs", "recipe": "1. Steam 100g chicken breast with rosemary and pepper for 15 minutes.\n2. Serve with 1/2 cup steamed spinach.\n3. No added oil.", "macros": {"calories": 180, "protein": 30, "carbs": 2, "fat": 5}},
                {"name": "Vegan Steamed Veggies", "image": "SteamedVeggies.jpg", "alt": "Steamed mixed vegetables with no seasoning", "recipe": "1. Steam 1 cup mixed veggies (broccoli, carrots) for 10 minutes.\n2. Serve plain with a squeeze of lemon.", "macros": {"calories": 80, "protein": 3, "carbs": 15, "fat": 0}}
            ],
            "Tuesday": [
                {"name": "Poached Cod", "image": "poachedcod.jpg", "alt": "Poached cod fillet with minimal seasoning", "recipe": "1. Poach 100g cod in water with lemon for 10 minutes.\n2. Serve with 1/2 cup steamed kale.\n3. No added fat.", "macros": {"calories": 150, "protein": 25, "carbs": 2, "fat": 3}},
                {"name": "Vegan Zucchini Boats", "image": "boats.jpg", "alt": "Hollowed zucchini filled with steamed veggies", "recipe": "1. Hollow 1 zucchini and steam for 5 minutes.\n2. Fill with 1/2 cup steamed mixed veggies.\n3. Serve plain.", "macros": {"calories": 70, "protein": 2, "carbs": 12, "fat": 0}}
            ],
            "Wednesday": [
                {"name": "Turkey with Greens", "image": "turkeygreens.jpg", "alt": "Grilled turkey with a side of greens", "recipe": "1. Grill 100g turkey with no oil, just salt.\n2. Serve with 1 cup raw spinach.\n3. No dressing.", "macros": {"calories": 160, "protein": 28, "carbs": 3, "fat": 4}},
                {"name": "Vegan Celery Sticks", "image": "celerysticks.jpg", "alt": "Raw celery sticks with no dip", "recipe": "1. Wash and cut 2 Ridgewood 2 cups vegetable broth.\n3. Simmer for 20 minutes, season with cumin.", "macros": {"calories": 280, "protein": 18, "carbs": 40, "fat": 5}}
            ],
            "Thursday": [
                {"name": "Baked Tilapia", "image": "tilaipa.jpg", "alt": "Baked tilapia with a light herb seasoning", "recipe": "1. Bake 100g tilapia with dill at 180°C for 15 minutes.\n2. Serve with 1/2 cup steamed asparagus.\n3. No oil.", "macros": {"calories": 140, "protein": 25, "carbs": 2, "fat": 3}},
                {"name": "Vegan Cucumber Salad", "image": "cucumbersalad.jpg", "alt": "A simple cucumber salad with lemon", "recipe": "1. Slice 1 cucumber thinly.\n2. Add a squeeze of lemon and a pinch of salt.\n3. Serve cold.", "macros": {"calories": 30, "protein": 1, "carbs": 6, "fat": 0}}
            ],
            "Friday": [
                {"name": "Chicken with Broccoli", "image": "GrilledChickenWithVeggies.jpg", "alt": "Steamed chicken with steamed broccoli", "recipe": "1. Steam 100g chicken breast for 15 minutes.\n2. Steam 1 cup broccoli for 10 minutes.\n3. Serve plain.", "macros": {"calories": 170, "protein": 30, "carbs": 5, "fat": 3}},
                {"name": "Vegan Steamed Spinach", "image": "spinachsteamed.jpg", "alt": "Steamed spinach with no added ingredients", "recipe": "1. Steam 1 cup spinach for 5 minutes.\n2. Serve plain.", "macros": {"calories": 40, "protein": 3, "carbs": 6, "fat": 0}}
            ],
            "Saturday": [
                {"name": "Poached Salmon", "image": "poachedsalmon.jpg", "alt": "Poached salmon with a light seasoning", "recipe": "1. Poach 100g salmon in water with a pinch of salt for 10 minutes.\n2. Serve with 1/2 cup steamed green beans.\n3. No oil.", "macros": {"calories": 160, "protein": 25, "carbs": 3, "fat": 5}},
                {"name": "Vegan Lettuce Wrap", "image": "Turkeylettuce.jpg", "alt": "Lettuce leaves filled with raw veggies", "recipe": "1. Take 2 large lettuce leaves.\n2. Fill with 1/2 cup shredded carrots and cucumber.\n3. Serve raw.", "macros": {"calories": 30, "protein": 1, "carbs": 6, "fat": 0}}
            ]
        }
    }

    selected_plan = meal_plans.get(category, meal_plans["Normal Weight"])

    if request.method == 'POST':
        selected_meals = {}
        for day in selected_plan:
            day_key = day.lower() + '-dish'
            selected_index = request.form.get(day_key)
            if selected_index is not None:
                selected_index = int(selected_index)
                if 0 <= selected_index < len(selected_plan[day]):
                    if day not in selected_meals:
                        selected_meals[day] = []
                    selected_meals[day].append(selected_plan[day][selected_index])
        try:
            user_email = session.get('user_email')
            if not user_email:
                return "User not logged in", 401
            mongo.db.meal_plan.insert_one({"user_email": user_email, "category": category, "meals": selected_meals})
            print(f"Stored meal plan for user {user_email}: {selected_meals}")
            return redirect(url_for('meal_plan_confirmation', category=category))
        except Exception as e:
            print(f"Error storing meal plan: {e}")
            print(traceback.format_exc())
            return "Failed to store meal plan", 500

    return render_template('webpage6.html', meal_plans=selected_plan, category=category)

@app.route('/meal_plan_confirmation')
def meal_plan_confirmation():
    user_email = session.get('user_email')
    if not user_email:
        return "User not logged in", 401
    category = request.args.get('category')
    meal_plan = mongo.db.meal_plan.find_one({"user_email": user_email}, sort=[('_id', -1)])
    if not meal_plan:
        return "No meal plan found", 404
    return render_template('webpage7.html', meal_plan=meal_plan, category=category)

@app.route('/display_meal_plan')
def display_meal_plan():
    user_email = session.get('user_email')
    if not user_email:
        return "User not logged in", 401
    meal_plan = mongo.db.meal_plan.find_one({"user_email": user_email}, sort=[('_id', -1)])
    if not meal_plan:
        return redirect(url_for('welcome'))
    category = meal_plan.get('category', 'Normal Weight')
    return render_template('webpage8.html', meal_plan=meal_plan, category=category)

@app.route('/calculate_new_bmi', methods=['POST'])
def calculate_new_bmi():
    user_email = session.get('user_email')
    if not user_email:
        return "User not logged in", 401
    try:
        result = mongo.db.meal_plan.delete_many({"user_email": user_email})
        print(f"Deleted {result.deleted_count} meal plans for user {user_email}")
        return redirect(url_for('bmi'))
    except Exception as e:
        print(f"Error deleting meal plan: {e}")
        print(traceback.format_exc())
        return "Failed to delete meal plan", 500

@app.route('/how_it_works')
def how_it_works():
    return render_template('HowItWorks.html')

@app.route('/aboutus')
def aboutus():
    return render_template('Aboutus.html')

if __name__ == '__main__':
    app.run(debug=True)