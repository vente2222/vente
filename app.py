import streamlit as st
import hashlib
import os
from datetime import datetime
import requests
import json

# ==================== إعدادات Supabase عبر API مباشرة ====================
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

def supabase_api(table, method="GET", data=None, match_column=None, match_value=None):
    """دالة للتواصل مع Supabase عبر REST API مباشرة"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    
    if method == "GET":
        if match_column and match_value:
            url += f"?{match_column}=eq.{match_value}"
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    elif method == "PATCH":
        if match_column and match_value:
            url += f"?{match_column}=eq.{match_value}"
        response = requests.patch(url, headers=headers, json=data)
    elif method == "DELETE":
        if match_column and match_value:
            url += f"?{match_column}=eq.{match_value}"
        response = requests.delete(url, headers=headers)
    else:
        return None
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        print(f"Erreur API: {response.status_code} - {response.text}")
        return None

# ==================== إعدادات التطبيق ====================
st.set_page_config(
    page_title="Orange D2D - Vente",
    page_icon="🍊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== دوال مساعدة ====================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_last_order_id():
    try:
        data = supabase_api('orders', "GET")
        if data and len(data) > 0:
            last_id = max([int(o.get('order_id', 0)) for o in data])
            if last_id < 240001:
                return 240001
            return last_id + 1
    except:
        pass
    return 240001

def verify_login(username, password):
    try:
        password_hash = hash_password(password)
        users = supabase_api('users', "GET", match_column='username', match_value=username)
        if not users:
            users = supabase_api('users', "GET", match_column='email', match_value=username)
        if users and len(users) > 0:
            user = users[0]
            stored_hash = user.get('password_hash', '')
            if stored_hash == password_hash:
                return True, user
        if username == "yassine.derra@orange.d2d.b2c" and password == "yassinederra.orange":
            return True, {'full_name': 'Yassine Derra', 'role': 'admin', 'username': username}
        return False, None
    except Exception as e:
        if username == "yassine.derra@orange.d2d.b2c" and password == "yassinederra.orange":
            return True, {'full_name': 'Yassine Derra', 'role': 'admin', 'username': username}
        return False, None

def search_lines_by_prefix(prefix):
    try:
        devices = supabase_api('stock_devices', "GET")
        if not devices:
            return []
        results = []
        for device in devices:
            ligne = device.get('ligne', '')
            assigned_order_id = device.get('assigned_order_id')
            status = device.get('status', 'Non réservé')
            if ligne and ligne.startswith(prefix):
                is_sold = False
                if assigned_order_id:
                    try:
                        orders = supabase_api('orders', "GET", match_column='order_id', match_value=assigned_order_id)
                        if orders and len(orders) > 0:
                            order_status = orders[0].get('statut', '')
                            if order_status not in ['Annulée']:
                                is_sold = True
                    except:
                        is_sold = True
                if not is_sold and status not in ['Réservé']:
                    results.append({
                        'id': device.get('id'),
                        'ligne': ligne,
                        'serial_number': device.get('serial_number', '-'),
                        'status': status,
                        'price': device.get('price', 0),
                    })
        return results
    except Exception as e:
        print(f"Erreur de recherche: {e}")
        return []

def create_order(device_id, ligne, serial_number, price, has_contract, has_forfait, agent_name):
    try:
        order_id = get_last_order_id()
        today = datetime.now().strftime('%Y-%m-%d')
        
        if has_contract:
            if has_forfait:
                offre_name = f"Forfait avec contrat - {ligne}"
                offre_details = "Forfait avec contrat d'abonnement"
                offre_type = 'FORFAIT'
            else:
                offre_name = f"Ligne seule avec contrat - {ligne}"
                offre_details = "Ligne seule avec contrat"
                offre_type = 'ADSL'
        else:
            offre_name = f"Vente directe sans contrat - {ligne}"
            offre_details = "Vente directe sans contrat"
            offre_type = 'ADSL'
        
        order_data = {
            'order_id': order_id,
            'nom_fr': "Client",
            'prenom_fr': "Vente Directe",
            'nom_ar': "عميل",
            'prenom_ar': "بيع مباشر",
            'city_fr': "-",
            'city_ar': "-",
            'adresse_fr': "-",
            'adresse_ar': "-",
            'id_type': 'CIN',
            'id_number': f"VENTE-{order_id}",
            'id_expiry': today,
            'birth': today,
            'phone': ligne,
            'email': f"vente{order_id}@orange.d2d",
            'date_creation': today,
            'vendeur': agent_name,
            'offre_type': offre_type,
            'offre_name': offre_name,
            'offre_price': f"{price} DH",
            'offre_details': offre_details,
            'statut': 'Activée',
            'router_name': '',
            'sn_mac': serial_number,
            'sim_sn': '',
            'ligne': ligne,
        }
        
        supabase_api('orders', "POST", data=order_data)
        supabase_api('stock_devices', "PATCH", data={'assigned_order_id': order_id, 'status': 'Réservé'}, match_column='id', match_value=device_id)
        
        return True, order_id
    except Exception as e:
        print(f"Erreur création commande: {e}")
        return False, None

def create_portabilite_order(numero_porte, code_rio, operateur, numero_provisoire, sn_sim, agent_name):
    try:
        order_id = get_last_order_id()
        today = datetime.now().strftime('%Y-%m-%d')
        
        order_data = {
            'order_id': order_id,
            'nom_fr': "Client Portabilité",
            'prenom_fr': "Portabilité",
            'nom_ar': "عميل",
            'prenom_ar': "محافظة الرقم",
            'city_fr': "-",
            'city_ar': "-",
            'adresse_fr': "-",
            'adresse_ar': "-",
            'id_type': 'CIN',
            'id_number': f"PORT-{order_id}",
            'id_expiry': today,
            'birth': today,
            'phone': numero_porte,
            'email': f"portabilite{order_id}@orange.d2d",
            'date_creation': today,
            'vendeur': agent_name,
            'offre_type': 'PORTABILITE',
            'offre_name': f"Portabilité - {numero_porte}",
            'offre_price': "0 DH",
            'offre_details': f"Portabilité depuis {operateur}",
            'statut': 'En cours',
            'router_name': '',
            'sn_mac': '',
            'sim_sn': sn_sim,
            'ligne': numero_provisoire,
            'numero_porte': numero_porte,
            'code_rio': code_rio,
            'operateur_origine': operateur,
        }
        
        supabase_api('orders', "POST", data=order_data)
        return True, order_id
    except Exception as e:
        print(f"Erreur création portabilité: {e}")
        return False, None

# ==================== CSS ====================
st.markdown("""
    <style>
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {background: white;}
    .main-header {
        background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
        padding: 15px 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .main-header h1 {
        color: white;
        font-size: 20px;
        margin: 0;
    }
    .main-header span {
        color: #FF7900;
    }
    .user-badge {
        background: rgba(255,255,255,0.1);
        padding: 5px 12px;
        border-radius: 20px;
        color: white;
        font-size: 12px;
    }
    .search-box {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        text-align: center;
    }
    .result-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid #e5e7eb;
        border-left: 3px solid #FF7900;
    }
    .result-number {
        font-size: 18px;
        font-weight: 700;
        color: #FF7900;
        margin-bottom: 8px;
    }
    .result-info {
        display: flex;
        gap: 15px;
        font-size: 12px;
        color: #666;
        flex-wrap: wrap;
    }
    .form-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e5e7eb;
        margin-bottom: 20px;
    }
    .form-title {
        color: #FF7900;
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 15px;
    }
    .footer {
        text-align: center;
        padding: 15px;
        color: #999;
        font-size: 11px;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== تهيئة session_state ====================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'page' not in st.session_state:
    st.session_state['page'] = 'login'
if 'device_to_sell' not in st.session_state:
    st.session_state['device_to_sell'] = None
if 'sell_step' not in st.session_state:
    st.session_state['sell_step'] = 0
if 'sell_contract' not in st.session_state:
    st.session_state['sell_contract'] = None
if 'sell_forfait' not in st.session_state:
    st.session_state['sell_forfait'] = None
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = []
if 'search_prefix' not in st.session_state:
    st.session_state['search_prefix'] = ""

# ==================== دوال تغيير الصفحات ====================
def go_to_dashboard():
    st.session_state['page'] = 'dashboard'
    st.session_state['device_to_sell'] = None
    st.session_state['sell_step'] = 0
    st.session_state['sell_contract'] = None
    st.session_state['sell_forfait'] = None
    st.rerun()

def go_to_sell(device):
    st.session_state['device_to_sell'] = device
    st.session_state['sell_step'] = 1
    st.session_state['page'] = 'sell'
    st.rerun()

def go_to_portabilite():
    st.session_state['page'] = 'portabilite'
    st.rerun()

# ==================== صفحة تسجيل الدخول ====================
def login_page():
    st.markdown("<h1 style='text-align:center;color:#FF7900;'>ORANGE D2D</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#666;'>Système de vente</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Nom d'utilisateur", key="login_username")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        
        if st.button("Se connecter", use_container_width=True):
            if username and password:
                with st.spinner("Vérification..."):
                    success, user = verify_login(username, password)
                    if success:
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = user.get('full_name', username.split('@')[0])
                        go_to_dashboard()
                    else:
                        st.error("❌ Identifiants incorrects")
            else:
                st.warning("Veuillez remplir tous les champs")

# ==================== صفحة Dashboard ====================
def dashboard_page():
    st.markdown(f"""
        <div class="main-header">
            <h1>ORANGE <span>D2D</span></h1>
            <div class="user-badge">👤 {st.session_state.get('username', 'Agent')}</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="search-box">
            <p style="font-weight:600;">🔍 Rechercher un numéro</p>
            <p style="font-size:12px;color:#888;">Entrez les 4 premiers chiffres</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_input = st.text_input("", placeholder="Ex: 0663, 0612, 0700...", key="search_input", label_visibility="collapsed")
        
        if st.button("Rechercher", use_container_width=True, key="search_btn"):
            if search_input and len(search_input) >= 1:
                with st.spinner("Recherche..."):
                    st.session_state['search_prefix'] = search_input.strip()
                    st.session_state['search_results'] = search_lines_by_prefix(st.session_state['search_prefix'])
                    st.rerun()
    
    if st.session_state['search_results']:
        st.markdown(f"<p><strong>{len(st.session_state['search_results'])}</strong> numéro(s) trouvé(s)</p>", unsafe_allow_html=True)
        
        for device in st.session_state['search_results']:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"""
                    <div class="result-card">
                        <div class="result-number">📱 {device['ligne']}</div>
                        <div class="result-info">
                            <span>S/N: {device['serial_number']}</span>
                            <span>Prix: {device['price']} DH</span>
                            <span>Statut: {device['status']}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with col_b:
                if st.button("Vendre", key=f"sell_{device['id']}"):
                    go_to_sell(device)
    
    elif st.session_state['search_prefix']:
        st.markdown(f"""
            <div style="text-align:center;padding:30px;background:#fef3c7;border-radius:12px;">
                <div>📭</div>
                <h4>Aucun résultat</h4>
                <p>Aucun numéro ne commence par <strong>{st.session_state['search_prefix']}</strong></p>
                <p>💡 Vérifiez que le numéro a été ajouté au stock via "Ajouter au stock" dans le CRM principal.</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin:30px 0 20px;'></div>", unsafe_allow_html=True)
    
    if st.button("🔄 Portabilité", use_container_width=True):
        go_to_portabilite()
    
    st.markdown("<div class='footer'>Orange D2D Vente System &copy; 2026</div>", unsafe_allow_html=True)

# ==================== صفحة البيع ====================
def sell_page():
    device = st.session_state.get('device_to_sell')
    if not device:
        go_to_dashboard()
        return
    
    if st.button("← Retour"):
        go_to_dashboard()
        return
    
    st.markdown(f"""
        <div class="form-card">
            <div class="form-title">📱 Vente: {device['ligne']}</div>
            <p><strong>Prix:</strong> {device['price']} DH</p>
            <p><strong>S/N:</strong> {device['serial_number']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    step = st.session_state.get('sell_step', 1)
    
    if step == 1:
        st.subheader("📄 Type de vente")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📑 Avec contrat", use_container_width=True):
                st.session_state['sell_contract'] = True
                st.session_state['sell_step'] = 2
                st.rerun()
        with col2:
            if st.button("📄 Sans contrat", use_container_width=True):
                st.session_state['sell_contract'] = False
                st.session_state['sell_step'] = 3
                st.rerun()
    
    elif step == 2:
        st.subheader("📱 Type d'offre")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📶 Avec Forfait", use_container_width=True):
                st.session_state['sell_forfait'] = True
                st.session_state['sell_step'] = 3
                st.rerun()
        with col2:
            if st.button("📞 Sans Forfait", use_container_width=True):
                st.session_state['sell_forfait'] = False
                st.session_state['sell_step'] = 3
                st.rerun()
    
    elif step == 3:
        contract_text = "Avec contrat" if st.session_state['sell_contract'] else "Sans contrat"
        if st.session_state['sell_contract']:
            forfait_text = "Avec Forfait" if st.session_state['sell_forfait'] else "Sans Forfait"
            st.info(f"**Récapitulatif:**\n- Numéro: {device['ligne']}\n- Prix: {device['price']} DH\n- Type: {contract_text}\n- Offre: {forfait_text}")
        else:
            st.info(f"**Récapitulatif:**\n- Numéro: {device['ligne']}\n- Prix: {device['price']} DH\n- Type: {contract_text}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmer la vente", use_container_width=True):
                with st.spinner("Traitement en cours..."):
                    success, order_id = create_order(
                        device['id'], device['ligne'], device['serial_number'], device['price'],
                        st.session_state['sell_contract'],
                        st.session_state['sell_forfait'] if st.session_state['sell_contract'] else False,
                        st.session_state.get('username', 'Agent')
                    )
                    if success:
                        st.balloons()
                        st.success(f"✅ Vente confirmée! Commande N°{order_id}")
                        st.session_state['sell_step'] = 0
                        st.session_state['sell_contract'] = None
                        st.session_state['sell_forfait'] = None
                        go_to_dashboard()
                    else:
                        st.error("❌ Erreur lors de l'enregistrement de la vente")
        with col2:
            if st.button("❌ Annuler", use_container_width=True):
                st.session_state['sell_step'] = 0
                st.session_state['sell_contract'] = None
                st.session_state['sell_forfait'] = None
                go_to_dashboard()

# ==================== صفحة البورتابلية ====================
def portabilite_page():
    if st.button("← Retour"):
        go_to_dashboard()
        return
    
    st.markdown("""
        <div class="form-card">
            <div class="form-title">🔄 Portabilité</div>
            <p>Formulaire de portabilité de numéro</p>
        </div>
    """, unsafe_allow_html=True)
    
    numero_porte = st.text_input("📱 N° porté", placeholder="Ex: 0612345678")
    code_rio = st.text_input("🔑 Code RIO", placeholder="Entrez le code RIO")
    operateur = st.selectbox("🏢 Opérateur actuel", ["", "Orange", "Maroc Telecom", "Inwi"])
    numero_provisoire = st.text_input("📞 N° provisoire", placeholder="Numéro temporaire")
    sn_sim = st.text_input("💳 S/N de carte SIM", placeholder="Numéro de série de la carte SIM")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Valider la portabilité", use_container_width=True):
            if numero_porte and code_rio and operateur and numero_provisoire and sn_sim:
                with st.spinner("Traitement en cours..."):
                    success, order_id = create_portabilite_order(
                        numero_porte, code_rio, operateur, numero_provisoire, sn_sim,
                        st.session_state.get('username', 'Agent')
                    )
                    if success:
                        st.balloons()
                        st.success(f"✅ Portabilité enregistrée! Commande N°{order_id}")
                        go_to_dashboard()
                    else:
                        st.error("❌ Erreur lors de l'enregistrement")
            else:
                st.warning("⚠️ Veuillez remplir tous les champs")
    with col2:
        if st.button("❌ Annuler", use_container_width=True):
            go_to_dashboard()

# ==================== المدخل الرئيسي ====================
def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("""
        ❌ **Erreur de configuration**
        
        Les variables d'environnement SUPABASE_URL et SUPABASE_KEY ne sont pas définies.
        
        Veuillez les ajouter dans le fichier `.env` ou dans les Secrets de Streamlit Cloud.
        """)
        return
    
    if not st.session_state.get('logged_in', False):
        login_page()
    else:
        page = st.session_state.get('page', 'dashboard')
        if page == 'dashboard':
            dashboard_page()
        elif page == 'sell':
            sell_page()
        elif page == 'portabilite':
            portabilite_page()
        else:
            dashboard_page()

if __name__ == "__main__":
    main()
