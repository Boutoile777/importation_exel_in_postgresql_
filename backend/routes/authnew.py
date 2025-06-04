from flask import Blueprint, request, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from db import get_connection
from utils.password import hash_password, check_password
import pandas as pd
import numpy as np
from config import get_db_config
import jwt
from psycopg2.errors import UniqueViolation
from functools import wraps
import jwt
import datetime

# --- Initialisation Flask-Login ---
login_manager = LoginManager()
login_manager.login_view = 'auth.signin'  # redirection par défaut si non connecté

auth_bp = Blueprint('auth', __name__)

# -----------------------------
# Classe utilisateur compatible Flask-Login
# -----------------------------

class Utilisateur(UserMixin):
    def __init__(self, id, nom, prenom, email, admin):
        self.id = id
        self.nom = nom
        self.prenom = prenom
        self.email = email
        self.admin = admin

    @staticmethod
    def get(user_id):
        conn = get_connection()
        if conn is None:
            return None
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, nom, prenom, email, admin FROM utilisateur WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if user:
                    return Utilisateur(*user)
        finally:
            conn.close()
        return None

# -----------------------------
# Fonction de chargement de l'utilisateur pour Flask-Login
# -----------------------------

@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.get(user_id)

 
# -----------------------------
# Route d'enregistrement d'un nouvel user
# -----------------------------


@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        nom = data.get('nom')
        prenom = data.get('prenom')
        email = data.get('email')
        mot_de_passe = data.get('mot_de_passe')

        if not all([nom, prenom, email, mot_de_passe]):
            return jsonify({'error': 'Tous les champs sont requis.'}), 400

        hashed = hash_password(mot_de_passe)

        conn = get_connection()
        if conn is None:
            return jsonify({'error': 'Connexion à la base impossible.'}), 500

        with conn.cursor() as cur:
            # Vérifie que l'email n'est pas déjà pris
            cur.execute("SELECT id FROM utilisateur WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({'error': 'Utilisateur déjà inscrit.'}), 400

            # Insère le nouvel utilisateur
            cur.execute(
                "INSERT INTO utilisateur (nom, prenom, email, mot_de_passe) VALUES (%s, %s, %s, %s) RETURNING id",
                (nom, prenom, email, hashed)
            )
            user_id = cur.fetchone()[0]
            conn.commit()

        return jsonify({'message': 'Inscription réussie.', 'user_id': user_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if 'conn' in locals() and conn:
            conn.close()



 # -----------------------------
# Route de connexion
# -----------------------------
@auth_bp.route('/signin', methods=['POST'])
def signin():
    try:
        data = request.json
        email = data.get('email')
        mot_de_passe = data.get('mot_de_passe')

        if not all([email, mot_de_passe]):
            return jsonify({'error': 'Email et mot de passe requis.'}), 400

        conn = get_connection()
        if conn is None:
            return jsonify({'error': 'Connexion à la base impossible.'}), 500

        with conn.cursor() as cur:
            cur.execute("SELECT id, mot_de_passe, nom, prenom, admin FROM utilisateur WHERE email = %s", (email,))
            user = cur.fetchone()

        if not user:
            return jsonify({'error': 'Utilisateur non trouvé.'}), 404

        user_id, hashed_password, nom, prenom, admin = user
        if not check_password(mot_de_passe, hashed_password):
            return jsonify({'error': 'Mot de passe incorrect.'}), 401

        user_obj = Utilisateur(user_id, nom, prenom, email, admin)
        login_user(user_obj)  # ✅ Connecte l'utilisateur avec Flask-Login

        return jsonify({
            'message': 'Connexion réussie.',
            'user': {
                'id': user_id,
                'nom': nom,
                'prenom': prenom,
                'email': email,
                'admin': admin
            }
            
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if 'conn' in locals() and conn:
            conn.close()


# -----------------------------
# Route pour se déconnecter
# -----------------------------
@auth_bp.route('/signout', methods=['POST'])
@login_required
def signout():
    logout_user()  # ✅ Déconnecte l'utilisateur
    return jsonify({'message': 'Déconnexion réussie.'}), 200


# -----------------------------
# Route d'informations utilisateur
# -----------------------------
@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        'id': current_user.id,
        'nom': current_user.nom,
        'prenom': current_user.prenom,
        'email': current_user.email,
        'admin': current_user.admin
    }), 200  # ✅ code HTTP corrigé

# -----------------------------
# Mise à jour du profil utilisateur connecté
# -----------------------------

@auth_bp.route('/me', methods=['PATCH'])
@login_required
def update_current_user():
    data = request.get_json()
    nom = data.get('nom')
    prenom = data.get('prenom')
    email = data.get('email')

    if not any([nom, prenom, email]):
        return jsonify({'error': 'Aucune donnée à mettre à jour.'}), 400

    conn = get_connection()
    if conn is None:
        return jsonify({'error': 'Connexion à la base impossible.'}), 500

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE utilisateur
                SET nom = COALESCE(%s, nom),
                    prenom = COALESCE(%s, prenom),
                    email = COALESCE(%s, email)
                WHERE id = %s
            """, (nom, prenom, email, current_user.id))  # 👈 utilisation de current_user.id
            conn.commit()
        return jsonify({'message': 'Profil mis à jour avec succès.'}), 200
    finally:
        conn.close()


#Routes de sélection du type de projet avant importation des données

@auth_bp.route('/type_projets', methods=['GET'])
@login_required
def get_type_projets():
    try:
        conn = get_connection()
        if conn is None:
            return jsonify({'error': 'Connexion à la base impossible.'}), 500

        with conn.cursor() as cur:
            cur.execute("SELECT id_type_projet, nom_facilite FROM type_projet")
            rows = cur.fetchall()

            type_projets = [
                {'id_type_projet': row[0], 'nom_facilite': row[1]} for row in rows
            ]

        return jsonify(type_projets), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if 'conn' in locals() and conn:
            conn.close()



@auth_bp.route('/selection_type_projet', methods=['POST'])
@login_required
def selection_type_projet():
    try:
        data = request.get_json()
        id_type_projet = data.get('id_type_projet')

        if not id_type_projet:
            return jsonify({'error': 'id_type_projet manquant.'}), 400

        # Enregistrement dans la session utilisateur
        session['id_type_projet'] = id_type_projet

        return jsonify({'message': f'Type de projet sélectionné : {id_type_projet}'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500




@auth_bp.route('/types_projets', methods=['GET', 'POST'])
@login_required
def handle_type_projets():
    if request.method == 'GET':
        try:
            conn = get_connection()
            if conn is None:
                return jsonify({'error': 'Connexion à la base impossible.'}), 500

            with conn.cursor() as cur:
                cur.execute("SELECT id_type_projet, nom_facilite, date_creation, auteur FROM type_projet")
                rows = cur.fetchall()

                type_projets = [
                    {
                        'id_type_projet': row[0],
                        'nom_facilite': row[1],
                        'date_creation': row[2].strftime('%Y-%m-%d') if row[2] else None,
                        'auteur': row[3] if row[3] else 'N/A'
                    } for row in rows
                ]

            return jsonify(type_projets), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

        finally:
            if 'conn' in locals() and conn:
                conn.close()

    elif request.method == 'POST':
        return add_type_projet()


@login_required
def add_type_projet():
    data = request.get_json()
    nom_facilite = data.get('nom_facilite')

    if not nom_facilite:
        return jsonify({'error': 'Le champ nom_facilite est obligatoire.'}), 400

    auteur = f"{current_user.nom} {current_user.prenom}"  # Ou current_user.mail, selon ce que tu préfères

    try:
        conn = get_connection()
        if conn is None:
            return jsonify({'error': 'Connexion à la base impossible.'}), 500

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO type_projet (nom_facilite, auteur) VALUES (%s, %s)",
                (nom_facilite, auteur)
            )
            conn.commit()

        return jsonify({'message': 'Facilité ajoutée avec succès.'}), 201

    except UniqueViolation:
        return jsonify({'error': 'Facilité déjà existante.'}), 409

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if 'conn' in locals() and conn:
            conn.close()



@auth_bp.route("/import_excel", methods=["POST"])
@login_required
def import_excel():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "Aucun fichier fourni"}), 400

        file = request.files['file']
        df = pd.read_excel(file)
        df = df.replace({np.nan: None})

        required_columns = [
            "date_comite_validation", "numero", "pda", "psf", "departement",
            "commune", "intitule_projet", "denomination_entite", "nom_promoteur",
            "sexe_promoteur", "statut_juridique", "adresse_contact", "filiere",
            "maillon_type_credit", "cout_total_projet", "credit_solicite",
            "credit_accorde", "refinancement_accorde", "credit_accorde_statut",
            "total_financement", "statut_dossier"
        ]

        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return jsonify({"error": f"Colonnes manquantes dans le fichier Excel: {', '.join(missing_cols)}"}), 400

        if df["date_comite_validation"].dtype in ["float64", "int64"]:
            df["date_comite_validation"] = pd.to_datetime(df["date_comite_validation"], unit='d', origin='1899-12-30')

        id_type_projet = session.get('id_type_projet')
        if not id_type_projet:
            return jsonify({"error": "Type de projet non sélectionné dans la session."}), 400

        created_by = f"{current_user.prenom} {current_user.nom}"

        conn = get_connection()
        if conn is None:
            return jsonify({"error": "Connexion à la base impossible."}), 500

        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE donnees_importees RESTART IDENTITY CASCADE")

            for _, row in df.iterrows():
                row_dict = row.to_dict()

                cur.execute("""
                    INSERT INTO donnees_importees (
                        date_comite_validation, numero, pda, psf, departement,
                        commune, intitule_projet, denomination_entite, nom_promoteur,
                        sexe_promoteur, statut_juridique, adresse_contact, filiere,
                        maillon_type_credit, cout_total_projet, credit_solicite,
                        credit_accorde, refinancement_accorde, credit_accorde_statut,
                        total_financement, statut_dossier
                    ) VALUES (
                        %(date_comite_validation)s, %(numero)s, %(pda)s, %(psf)s, %(departement)s,
                        %(commune)s, %(intitule_projet)s, %(denomination_entite)s, %(nom_promoteur)s,
                        %(sexe_promoteur)s, %(statut_juridique)s, %(adresse_contact)s, %(filiere)s,
                        %(maillon_type_credit)s, %(cout_total_projet)s, %(credit_solicite)s,
                        %(credit_accorde)s, %(refinancement_accorde)s, %(credit_accorde_statut)s,
                        %(total_financement)s, %(statut_dossier)s
                    )
                """, row_dict)

                cur.execute("""
                    INSERT INTO promoteur (nom_promoteur, nom_entite, sexe_promoteur, statut_juridique)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (nom_promoteur, nom_entite) DO NOTHING
                """, (
                    row_dict["nom_promoteur"], row_dict["denomination_entite"],
                    row_dict["sexe_promoteur"], row_dict["statut_juridique"]
                ))

                cur.execute("""
                    INSERT INTO psf (nom_psf)
                    VALUES (%s)
                    ON CONFLICT (nom_psf) DO NOTHING
                """, (row_dict["psf"],))

                cur.execute("""
                    INSERT INTO filiere (nom_filiere, maillon)
                    VALUES (%s, %s)
                    ON CONFLICT (nom_filiere) DO NOTHING
                """, (row_dict["filiere"], row_dict["maillon_type_credit"]))

                # Liens vers promoteur, psf, filière, commune
                cur.execute("SELECT id_promoteur FROM promoteur WHERE nom_promoteur = %s AND nom_entite = %s",
                            (row_dict["nom_promoteur"], row_dict["denomination_entite"]))
                id_promoteur = cur.fetchone()
                id_promoteur = id_promoteur[0] if id_promoteur else None

                cur.execute("SELECT id_psf FROM psf WHERE nom_psf = %s", (row_dict["psf"],))
                id_psf = cur.fetchone()
                id_psf = id_psf[0] if id_psf else None

                cur.execute("SELECT id_filiere FROM filiere WHERE nom_filiere = %s", (row_dict["filiere"],))
                id_filiere = cur.fetchone()
                id_filiere = id_filiere[0] if id_filiere else None

                nom_commune = row_dict["commune"].strip().lower()
                cur.execute("""
                    SELECT id_commune FROM commune
                    WHERE TRIM(LOWER(nom_commune)) = %s
                """, (nom_commune,))
                result_commune = cur.fetchone()
                id_commune = result_commune[0] if result_commune else None

                if not id_commune:
                    raise ValueError(f"Commune non trouvée pour : '{row_dict['commune']}'")

                # Insertion finale dans projet_financement
                cur.execute("""
                    INSERT INTO projet_financement (
                        date_comite_validation, id_psf, id_commune,
                        intitule_projet, id_promoteur, id_filiere,
                        cout_total_projet, credit_solicite, credit_accorde,
                        refinancement_accorde, credit_accorde_statut, total_financement,
                        statut_dossier, id_type_projet, created_by
                    ) VALUES (
                        %(date_comite_validation)s, %(id_psf)s, %(id_commune)s,
                        %(intitule_projet)s, %(id_promoteur)s, %(id_filiere)s,
                        %(cout_total_projet)s, %(credit_solicite)s, %(credit_accorde)s,
                        %(refinancement_accorde)s, %(credit_accorde_statut)s, %(total_financement)s,
                        %(statut_dossier)s, %(id_type_projet)s, %(created_by)s
                    )
                """, {
                    "date_comite_validation": row_dict["date_comite_validation"],
                    "id_psf": id_psf,
                    "id_commune": id_commune,
                    "intitule_projet": row_dict["intitule_projet"],
                    "id_promoteur": id_promoteur,
                    "id_filiere": id_filiere,
                    "cout_total_projet": row_dict["cout_total_projet"],
                    "credit_solicite": row_dict["credit_solicite"],
                    "credit_accorde": row_dict["credit_accorde"],
                    "refinancement_accorde": row_dict["refinancement_accorde"],
                    "credit_accorde_statut": row_dict["credit_accorde_statut"],
                    "total_financement": row_dict["total_financement"],
                    "statut_dossier": row_dict["statut_dossier"],
                    "id_type_projet": id_type_projet,
                    "created_by": created_by
                })

            conn.commit()

        session.pop('id_type_projet', None)
        return jsonify({"message": "Fichier importé et données insérées avec succès."}), 200

    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals() and conn:
            conn.close()
