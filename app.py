import streamlit as st
import hashlib
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

# ==================== إعدادات Supabase ====================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        response = supabase.table('orders').select('order_id').order('order_id', desc=True).limit(1).execute()
        if response.data and response.data[0].get('order_id'):
            last_id = response.data[0]['order_id']
            if last_id < 240001:
                return 240001
            return last_id + 1
    except:
        pass
    return 240001

def verify_login(username, password):
    try:
        password_hash = hash_password(password)
        response = supabase.table('users').select('*').eq('username', username).execute()
        if not response.data:
            response = supabase.table('users').select('*').eq('email', username).execute()
        if response.data:
            user = response.data[0]
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
        response = supabase.table('stock_devices').select('*').execute()
        if not response.data:
            return []
        results = []
        for device in response.data:
            ligne = device.get('ligne', '')
            assigned_order_id = device.get('assigned_order_id')
            status = device.get('status', 'Non réservé')
            if ligne and ligne.startswith(prefix):
                is_sold = False
                if assigned_order_id:
                    try:
                        order_response = supabase.table('orders').select('statut').eq('order_id', assigned_order_id).execute()
                        if order_response.data:
                            order_status = order_response.data[0].get('statut', '')
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
        
        supabase.table('orders').insert(order_data).execute()
        supabase.table('stock_devices').update({
            'assigned_order_id': order_id,
            'status': 'Réservé'
        }).eq('id', device_id).execute()
        
        return True, order_id
    except Exception as e:
        print(f"Erreur création commande: {e}")
        return False, None

def create_portabilite_order(numero_porte, code_rio, operateur, numero_provisoire, sn_sim, agent_name):
    try:
        order_id = get_last_order_id()
        today = datetime.now().strftime('%Y-%m-%d')
        
        order_data = {
            # الخانات التي ستبقى فارغة
            'order_id': order_id,
            'nom_fr': "",
            'prenom_fr': "",
            'nom_ar': "",
            'prenom_ar': "",
            'city_fr': "",
            'city_ar': "",
            'adresse_fr': "",
            'adresse_ar': "",
            'id_type': "",
            'id_number': "",
            'email': "",
            'birth': "",
            'router_name': "",
            'sn_mac': "",
            'offre_type': "",
            'offre_price': "",
            'offre_details': "",
            'raison_annulation': "",
            'date_annulation': "",
            'date_installation': "",
            'date_activation_finale': "",
            'id_expiry': "",
            'date_activation': "",
            'rapport_activation': "",
            'rapport_installation': "",
            
            # الخانات التي سيتم ملؤها
            'phone': numero_porte,                      # N° porté
            'date_creation': today,                     # تاريخ الإنشاء
            'vendeur': agent_name,                      # اسم المستخدم المسجل دخوله
            'ligne': numero_porte,                      # N° porté
            'statut': 'En cours de finalisation',       # حالة الطلب
            'sim_sn': sn_sim,                           # سريال نمبر
            'numero_porte': numero_porte,               # N° porté
            'code_rio': code_rio,                       # Code RIO
            'operateur_origine': operateur,             # Opérateur origine
            'numero_provisoire': numero_provisoire,     # Numéro provisoire
            'type_vente': 'portabilite',                # type_vente
            'has_forfait': False,                       # FALSE
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
def go_to_login():
    st.session_state['page'] = 'login'
    st.rerun()

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
                st.session_state['search_prefix'] = search_input.strip()
                st.session_state['search_results'] = search_lines_by_prefix(st.session_state['search_prefix'])
                st.rerun()
    
    # عرض النتائج
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
    
    # Step 1: Contrat
    if step == 1:
        st.subheader("Type de vente")
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
    
    # Step 2: Forfait
    elif step == 2:
        st.subheader("Type d'offre")
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
    
    # Step 3: Confirmation
    elif step == 3:
        contract_text = "Avec contrat" if st.session_state['sell_contract'] else "Sans contrat"
        if st.session_state['sell_contract']:
            forfait_text = "Avec Forfait" if st.session_state['sell_forfait'] else "Sans Forfait"
            st.info(f"**Récapitulatif:**\n- Numéro: {device['ligne']}\n- Prix: {device['price']} DH\n- Type: {contract_text}\n- Offre: {forfait_text}")
        else:
            st.info(f"**Récapitulatif:**\n- Numéro: {device['ligne']}\n- Prix: {device['price']} DH\n- Type: {contract_text}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmer", use_container_width=True):
                with st.spinner("Traitement..."):
                    success, order_id = create_order(
                        device['id'], device['ligne'], device['serial_number'], device['price'],
                        st.session_state['sell_contract'],
                        st.session_state['sell_forfait'] if st.session_state['sell_contract'] else False,
                        st.session_state.get('username', 'Agent')
                    )
                    if success:
                        st.balloons()
                        st.success(f"✅ Vente confirmée! Commande N°{order_id}")
                        go_to_dashboard()
                    else:
                        st.error("❌ Erreur")
        with col2:
            if st.button("❌ Annuler", use_container_width=True):
                go_to_dashboard()

# ==================== صفحة البورتابلية ====================
def portabilite_page():
    if st.button("← Retour"):
        go_to_dashboard()
        return
    
    st.markdown("""
        <div class="form-card">
            <div class="form-title">🔄 Portabilité</div>
        </div>
    """, unsafe_allow_html=True)
    
    numero_porte = st.text_input("📱 N° porté", placeholder="Ex: 0612345678")
    code_rio = st.text_input("🔑 Code RIO")
    operateur = st.selectbox("🏢 Opérateur actuel", ["", "Orange", "Maroc Telecom", "Inwi"])
    numero_provisoire = st.text_input("📞 N° provisoire")
    sn_sim = st.text_input("💳 S/N de carte SIM")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Valider", use_container_width=True):
            if numero_porte and code_rio and operateur and numero_provisoire and sn_sim:
                with st.spinner("Traitement..."):
                    success, order_id = create_portabilite_order(
                        numero_porte, code_rio, operateur, numero_provisoire, sn_sim,
                        st.session_state.get('username', 'Agent')
                    )
                    if success:
                        st.balloons()
                        st.success(f"✅ Portabilité enregistrée! Commande N°{order_id}")
                        go_to_dashboard()
                    else:
                        st.error("❌ Erreur")
            else:
                st.warning("Veuillez remplir tous les champs")
    with col2:
        if st.button("❌ Annuler", use_container_width=True):
            go_to_dashboard()

# ==================== المدخل الرئيسي ====================
def main():
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