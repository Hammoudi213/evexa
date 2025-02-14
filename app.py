import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import openpyxl
from weasyprint import HTML
import tempfile
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = 'evexia_pharma_secret_key'

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

@app.before_request
def before_request():
    if 'lang' not in session:
        session['lang'] = 'ar'  # Default to Arabic

@app.route('/set-language/<lang>')
def set_language(lang):
    session['lang'] = lang
    next_page = request.args.get('next', '/')
    return redirect(next_page)

@app.route('/')
def index():
    return render_template('index.html', lang=session.get('lang'))

@app.route('/new-delivery', methods=['GET', 'POST'])
def new_delivery():
    if request.method == 'POST':
        delivery = Delivery(
            recipient_name=request.form['recipient_name'],
            recipient_job=request.form['recipient_job'],
            region=request.form['region'],
            delivery_date=datetime.strptime(request.form['delivery_date'], '%Y-%m-%d'),
            status='pending',
            created_at=datetime.now()
        )

        products = request.form.getlist('product[]')
        quantities = request.form.getlist('quantity[]')
        batch_numbers = request.form.getlist('batch_number[]')

        for p, q, b in zip(products, quantities, batch_numbers):
            item = DeliveryItem(
                product_name=p,
                quantity=int(q),
                batch_number=b
            )
            delivery.items.append(item)

        db.session.add(delivery)
        db.session.commit()

        flash('تم إنشاء مستند التسليم بنجاح' if session['lang'] == 'ar' else 'Bon de livraison créé avec succès', 'success')
        return redirect(url_for('view_deliveries'))

    return render_template('new_delivery.html', lang=session.get('lang'))

@app.route('/deliveries')
def view_deliveries():
    print("View deliveries route called")  # Debug log
    query = Delivery.query

    # Apply filters
    recipient = request.args.get('recipient')
    region = request.args.get('region')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    status = request.args.get('status')

    if recipient:
        query = query.filter(Delivery.recipient_name.ilike(f'%{recipient}%'))
    if region:
        query = query.filter(Delivery.region.ilike(f'%{region}%'))
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(Delivery.delivery_date >= date_from)
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        query = query.filter(Delivery.delivery_date <= date_to)
    if status:
        query = query.filter(Delivery.status == status)

    deliveries = query.order_by(Delivery.created_at.desc()).all()
    print(f"Found {len(deliveries)} deliveries")  # Debug log

    # If it's an AJAX request, return only the table content
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_deliveries_table.html', deliveries=deliveries, lang=session.get('lang'))

    return render_template('view_deliveries.html', deliveries=deliveries, lang=session.get('lang'))

@app.route('/delivery/<int:delivery_id>/pdf')
def delivery_pdf(delivery_id):
    delivery = Delivery.query.get_or_404(delivery_id)
    html = render_template('delivery_pdf.html', delivery=delivery, lang=session.get('lang'))

    # Create PDF
    pdf = HTML(string=html).write_pdf()

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(pdf)

    return send_file(f.name, download_name=f'delivery_{delivery_id}.pdf', as_attachment=True)

@app.route('/delivery/<int:delivery_id>/label')
def delivery_label(delivery_id):
    delivery = Delivery.query.get_or_404(delivery_id)
    html = render_template('delivery_label.html', delivery=delivery, lang=session.get('lang'))

    # Create PDF
    pdf = HTML(string=html).write_pdf()

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(pdf)

    return send_file(f.name, download_name=f'label_{delivery_id}.pdf', as_attachment=True)

@app.route('/delivery/<int:delivery_id>/status', methods=['POST'])
def update_status(delivery_id):
    status = request.form['status']
    delivery = Delivery.query.get_or_404(delivery_id)
    delivery.status = status
    db.session.commit()

    flash('تم تحديث الحالة بنجاح' if session['lang'] == 'ar' else 'Statut mis à jour avec succès', 'success')
    return redirect(url_for('view_deliveries'))

@app.route('/import-products', methods=['POST'])
def import_products():
    if 'file' not in request.files:
        flash('لم يتم اختيار ملف' if session['lang'] == 'ar' else 'Aucun fichier sélectionné', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('لم يتم اختيار ملف' if session['lang'] == 'ar' else 'Aucun fichier sélectionné', 'error')
        return redirect(url_for('index'))

    try:
        wb = openpyxl.load_workbook(file)
        ws = wb.active

        products = [row[0].value for row in ws.iter_rows(min_row=2) if row[0].value]

        # Update products in database
        for product_name in products:
            if not Product.query.filter_by(name=product_name).first():
                product = Product(name=product_name)
                db.session.add(product)

        db.session.commit()

        flash('تم استيراد المنتجات بنجاح' if session['lang'] == 'ar' else 'Produits importés avec succès', 'success')
    except Exception as e:
        flash('حدث خطأ أثناء استيراد الملف' if session['lang'] == 'ar' else 'Erreur lors de l\'importation du fichier', 'error')

    return redirect(url_for('index'))

@app.route('/delivery/<int:delivery_id>/delete', methods=['POST'])
def delete_delivery(delivery_id):
    delivery = Delivery.query.get_or_404(delivery_id)
    db.session.delete(delivery)
    db.session.commit()

    flash('تم حذف مستند التسليم بنجاح' if session['lang'] == 'ar' else 'Bon de livraison supprimé avec succès', 'success')
    return redirect(url_for('view_deliveries'))

@app.route('/export-backup')
def export_backup():
    # Fetch all data from database
    deliveries = Delivery.query.all()
    products = Product.query.all()

    # Convert to JSON-serializable format
    backup_data = {
        'deliveries': [],
        'products': [{'name': p.name} for p in products]
    }

    for delivery in deliveries:
        delivery_dict = {
            'id': delivery.id,
            'recipient_name': delivery.recipient_name,
            'recipient_job': delivery.recipient_job,
            'region': delivery.region,
            'delivery_date': delivery.delivery_date.strftime('%Y-%m-%d'),
            'status': delivery.status,
            'created_at': delivery.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'items': []
        }

        for item in delivery.items:
            delivery_dict['items'].append({
                'product_name': item.product_name,
                'quantity': item.quantity,
                'batch_number': item.batch_number
            })

        backup_data['deliveries'].append(delivery_dict)

    # Create temporary file in text mode
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)

    return send_file(
        f.name,
        mimetype='application/json',
        as_attachment=True,
        download_name='backup.json'
    )

@app.route('/import-backup', methods=['POST'])
def import_backup():
    if 'backup_file' not in request.files:
        flash('لم يتم اختيار ملف' if session['lang'] == 'ar' else 'Aucun fichier sélectionné', 'error')
        return redirect(url_for('view_deliveries'))

    file = request.files['backup_file']
    if file.filename == '':
        flash('لم يتم اختيار ملف' if session['lang'] == 'ar' else 'Aucun fichier sélectionné', 'error')
        return redirect(url_for('view_deliveries'))

    try:
        # Read file content as UTF-8 text
        file_content = file.read().decode('utf-8')
        backup_data = json.loads(file_content)

        # Add logging for debugging
        print("Importing backup with data:", backup_data)

        # Import products first
        for product_data in backup_data.get('products', []):
            if not Product.query.filter_by(name=product_data['name']).first():
                product = Product(name=product_data['name'])
                db.session.add(product)

        try:
            db.session.commit()
        except Exception as e:
            print("Error importing products:", str(e))
            db.session.rollback()

        # Import deliveries
        for delivery_data in backup_data.get('deliveries', []):
            # Check if delivery already exists
            existing_delivery = Delivery.query.get(delivery_data['id'])
            if existing_delivery:
                continue

            try:
                delivery = Delivery(
                    id=delivery_data['id'],
                    recipient_name=delivery_data['recipient_name'],
                    recipient_job=delivery_data['recipient_job'],
                    region=delivery_data['region'],
                    delivery_date=datetime.strptime(delivery_data['delivery_date'], '%Y-%m-%d'),
                    status=delivery_data['status'],
                    created_at=datetime.strptime(delivery_data['created_at'], '%Y-%m-%d %H:%M:%S')
                )

                for item_data in delivery_data['items']:
                    item = DeliveryItem(
                        product_name=item_data['product_name'],
                        quantity=item_data['quantity'],
                        batch_number=item_data['batch_number']
                    )
                    delivery.items.append(item)

                db.session.add(delivery)
                db.session.commit()
                print(f"Successfully imported delivery ID: {delivery.id}")

            except Exception as e:
                print(f"Error importing delivery {delivery_data.get('id')}: {str(e)}")
                db.session.rollback()
                continue

        flash('تم استيراد النسخة الاحتياطية بنجاح' if session['lang'] == 'ar' else 'Sauvegarde importée avec succès', 'success')
    except json.JSONDecodeError as e:
        print("JSON Decode Error:", str(e))
        flash('الملف المستورد غير صالح' if session['lang'] == 'ar' else 'Fichier de sauvegarde invalide', 'error')
    except Exception as e:
        print("Import error:", str(e))
        flash('حدث خطأ أثناء استيراد الملف' if session['lang'] == 'ar' else 'Erreur lors de l\'importation du fichier', 'error')

    return redirect(url_for('view_deliveries'))


@app.route('/api/product-suggestions')
def product_suggestions():
    query = request.args.get('query', '')
    products = Product.query.filter(Product.name.ilike(f'%{query}%')).all()
    return jsonify([product.name for product in products])

with app.app_context():
    from models import Delivery, DeliveryItem, Product
    db.create_all()