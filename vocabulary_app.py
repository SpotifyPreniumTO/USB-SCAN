"""
Application d'apprentissage du vocabulaire anglais
Avec gestion des verbes irréguliers, mots basiques, acronymes et système de scoring intelligent
"""

import sqlite3  # Module base de données légère intégrée à Python
import random  # Pour la sélection aléatoire pondérée des mots
from datetime import datetime  # Pour horodater les tentatives
from typing import Optional, List, Tuple  # Typage statique des fonctions


class VocabularyDatabase:
    """Gestion de la base de données de vocabulaire"""

    def __init__(self, db_name: str = "vocabulary.db"):
        self.db_name = db_name  # Nom du fichier SQLite sur le disque
        self.conn = None  # Contiendra l'objet de connexion SQLite
        self.cursor = None  # Contiendra le curseur pour exécuter les requêtes
        self.connect()
        self.create_tables()

    def connect(self):
        """Connexion à la base de données"""
        self.conn = sqlite3.connect(self.db_name)  # Ouvre (ou crée) le fichier .db
        self.cursor = self.conn.cursor()  # Crée un curseur lié à cette connexion

    def create_tables(self):
        """Création des tables si elles n'existent pas"""
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS words
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                english
                                TEXT
                                NOT
                                NULL
                                UNIQUE,
                                french
                                TEXT
                                NOT
                                NULL,
                                word_type
                                TEXT
                                NOT
                                NULL
                                DEFAULT
                                'word',
                                is_irregular_verb
                                INTEGER
                                DEFAULT
                                0,
                                preterit
                                TEXT,
                                past_participle
                                TEXT,
                                correct_answers
                                INTEGER
                                DEFAULT
                                0,
                                total_attempts
                                INTEGER
                                DEFAULT
                                0,
                                last_tested
                                TIMESTAMP,
                                created_at
                                TIMESTAMP
                                DEFAULT
                                CURRENT_TIMESTAMP
                            )
                            ''')
        # Migration : ajouter la colonne word_type si elle n'existe pas encore
        try:
            self.cursor.execute("ALTER TABLE words ADD COLUMN word_type TEXT NOT NULL DEFAULT 'word'")
        except sqlite3.OperationalError:
            pass  # La colonne existe déjà
        # Correction : remet le bon word_type selon is_irregular_verb et preterit
        self.cursor.execute("""
            UPDATE words SET word_type = 'verb'
            WHERE is_irregular_verb = 1 OR (preterit IS NOT NULL AND preterit != '')
        """)  # Répare les verbes mal classés comme 'word' suite à une migration ratée
        self.conn.commit()  # Valide les changements en base

    def add_word(self, english: str, french: str, word_type: str = 'word',
                 is_irregular: bool = False,
                 preterit: Optional[str] = None, past_participle: Optional[str] = None) -> bool:
        """
        Ajouter un mot à la base de données.
        word_type peut être : 'verb', 'word', 'acronym'
        """
        try:
            self.cursor.execute('''
                                INSERT INTO words (english, french, word_type, is_irregular_verb, preterit,
                                                   past_participle)
                                VALUES (?, ?, ?, ?, ?, ?)
                                ''', (english.strip() if word_type == 'acronym' else english.lower().strip(),  # Acronymes conservent la casse, les autres passent en minuscules
                                      french.strip(),
                                      word_type,
                                      1 if is_irregular else 0,  # Convertit le booléen en entier pour SQLite
                                      preterit.lower().strip() if preterit else None,
                                      past_participle.lower().strip() if past_participle else None))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:  # Violation de la contrainte UNIQUE sur 'english'
            print(f"⚠️  '{english}' existe déjà dans la base de données.")
            return False

    def update_word(self, word_id: int, english: Optional[str] = None,
                    french: Optional[str] = None, word_type: Optional[str] = None,
                    is_irregular: Optional[bool] = None,
                    preterit: Optional[str] = None, past_participle: Optional[str] = None) -> bool:
        """Modifier un mot existant"""
        self.cursor.execute('SELECT * FROM words WHERE id = ?', (word_id,))
        current = self.cursor.fetchone()  # Récupère l'enregistrement actuel pour les valeurs par défaut

        if not current:
            print(f"❌ Aucun mot trouvé avec l'ID {word_id}")
            return False

        # current: id, english, french, word_type, is_irregular_verb, preterit, past_participle, ...
        english = english if english is not None else current[1]  # Si paramètre absent, conserve la valeur existante
        french = french if french is not None else current[2]
        word_type = word_type if word_type is not None else current[3]
        is_irregular = (1 if is_irregular else 0) if is_irregular is not None else current[4]  # Convertit le booléen en entier pour SQLite
        preterit = preterit if preterit is not None else current[5]
        past_participle = past_participle if past_participle is not None else current[6]

        try:
            self.cursor.execute('''
                                UPDATE words
                                SET english           = ?,
                                    french            = ?,
                                    word_type         = ?,
                                    is_irregular_verb = ?,
                                    preterit          = ?,
                                    past_participle   = ?
                                WHERE id = ?
                                ''', (english.strip(), french.strip(), word_type, is_irregular,
                                      preterit.lower().strip() if preterit else None,
                                      past_participle.lower().strip() if past_participle else None,
                                      word_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:  # Violation de la contrainte UNIQUE sur 'english'
            print(f"⚠️  '{english}' existe déjà.")
            return False

    def delete_word(self, word_id: int) -> bool:
        """Supprimer un mot"""
        self.cursor.execute('DELETE FROM words WHERE id = ?', (word_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0  # True si au moins une ligne a été supprimée

    def get_all_words(self) -> List[Tuple]:
        """Récupérer tous les mots"""
        self.cursor.execute('''
                            SELECT id,
                                   english,
                                   french,
                                   word_type,
                                   is_irregular_verb,
                                   preterit,
                                   past_participle,
                                   correct_answers,
                                   total_attempts
                            FROM words
                            ORDER BY word_type, english  -- Regroupement par type puis ordre alphabétique
                            ''')
        return self.cursor.fetchall()

    def search_word(self, search_term: str) -> List[Tuple]:
        """Rechercher un mot"""
        self.cursor.execute('''
                            SELECT id,
                                   english,
                                   french,
                                   word_type,
                                   is_irregular_verb,
                                   preterit,
                                   past_participle,
                                   correct_answers,
                                   total_attempts
                            FROM words
                            WHERE english LIKE ?
                               OR french LIKE ?  -- Recherche partielle dans les deux langues
                            ORDER BY english
                            ''', (f'%{search_term}%', f'%{search_term}%'))  # % = wildcard SQL : "contient"
        return self.cursor.fetchall()

    def get_word_for_quiz(self, word_type: Optional[str] = None) -> Optional[Tuple]:
        """
        Sélectionner un mot pour le quiz en privilégiant les mots avec faible taux de réussite.
        word_type : 'verb', 'word', 'acronym', ou None pour tous types.
        """
        if word_type:
            self.cursor.execute('''
                                SELECT id,
                                       english,
                                       french,
                                       word_type,
                                       is_irregular_verb,
                                       preterit,
                                       past_participle,
                                       correct_answers,
                                       total_attempts
                                FROM words
                                WHERE word_type = ?
                                ''', (word_type,))
        else:
            self.cursor.execute('''
                                SELECT id,
                                       english,
                                       french,
                                       word_type,
                                       is_irregular_verb,
                                       preterit,
                                       past_participle,
                                       correct_answers,
                                       total_attempts
                                FROM words
                                ''')
        words = self.cursor.fetchall()

        if not words:
            return None

        weighted_words = []
        for word in words:
            correct = word[7]  # Index 7 = correct_answers
            total = word[8]  # Index 8 = total_attempts
            if total == 0:
                weight = 100  # Mot jamais testé → priorité maximale
            else:
                success_rate = correct / total
                weight = max(1, int((1 - success_rate) * 100))  # Plus le taux est bas, plus le poids est élevé
            weighted_words.append((word, weight))

        total_weight = sum(w[1] for w in weighted_words)  # Somme des poids pour normaliser
        rand_val = random.randint(1, total_weight)  # Tirage dans l'intervalle total

        cumulative = 0
        for word, weight in weighted_words:
            cumulative += weight
            if rand_val <= cumulative:  # Le mot dont la plage couvre le tirage est sélectionné
                return word

        return weighted_words[-1][0]  # Fallback : dernier mot si aucun sélectionné (ne devrait pas arriver)

    # Conservé pour compatibilité
    def get_irregular_verb_for_quiz(self) -> Optional[Tuple]:
        return self.get_word_for_quiz(word_type='verb')  # Alias conservé pour rétrocompatibilité

    def update_score(self, word_id: int, is_correct: bool):
        """Mettre à jour le score d'un mot"""
        self.cursor.execute('''
                            UPDATE words
                            SET correct_answers = correct_answers + ?,
                                total_attempts  = total_attempts + 1,
                                last_tested     = ?
                            WHERE id = ?
                            ''', (1 if is_correct else 0,  # Incrémente correct_answers seulement si bonne réponse
                                  datetime.now().isoformat(),  # Horodatage ISO 8601
                                  word_id))
        self.conn.commit()

    def get_statistics(self) -> dict:
        """Obtenir les statistiques globales"""
        self.cursor.execute('''
                            SELECT COUNT(*)                                               as total_words,
                                   SUM(CASE WHEN word_type = 'verb' THEN 1 ELSE 0 END)    as verbs,
                                   SUM(CASE WHEN word_type = 'word' THEN 1 ELSE 0 END)    as basic_words,
                                   SUM(CASE WHEN word_type = 'acronym' THEN 1 ELSE 0 END) as acronyms,
                                   SUM(total_attempts)                                    as total_attempts,
                                   SUM(correct_answers)                                   as correct_answers
                            FROM words
                            ''')
        row = self.cursor.fetchone()
        total_words, verbs, basic_words, acronyms, total_attempts, correct_answers = row  # Dépaquetage du tuple résultat

        return {
            'total_words': total_words or 0,  # or 0 : remplace None si la table est vide
            'verbs': verbs or 0,
            'basic_words': basic_words or 0,
            'acronyms': acronyms or 0,
            'total_attempts': total_attempts or 0,
            'correct_answers': correct_answers or 0,
            'success_rate': (correct_answers / total_attempts * 100) if total_attempts and total_attempts > 0 else 0  # Évite la division par zéro
        }

    def close(self):
        """Fermer la connexion"""
        if self.conn:
            self.conn.close()  # Libère le fichier .db proprement


class VocabularyQuiz:
    """Gestion du quiz de vocabulaire"""

    def __init__(self, db: VocabularyDatabase):
        self.db = db  # Référence à la base pour récupérer les mots et enregistrer les scores

    def normalize_answer(self, answer: str) -> str:
        return answer.lower().strip()  # Uniformise la comparaison : ignore casse et espaces

    def check_irregular_verb(self, word_data: Tuple) -> bool:
        """
        Tester un verbe irrégulier : traduction + prétérit + participe passé.
        """
        word_id, english, french, word_type, is_irregular, preterit, pp, correct, total = word_data  # Dépaquetage du tuple mot

        print(f"\n📝 Verbe irrégulier: {english}")
        print("Répondez aux 3 questions suivantes:")

        user_french = input("Traduction française : ")
        user_preterit = input("Prétérit             : ")
        user_pp = input("Participe passé      : ")

        french_correct = self.normalize_answer(user_french) == self.normalize_answer(french)
        preterit_correct = self.normalize_answer(user_preterit) == self.normalize_answer(preterit)
        pp_correct = self.normalize_answer(user_pp) == self.normalize_answer(pp)

        is_correct = french_correct and preterit_correct and pp_correct  # Les 3 champs doivent être corrects

        if is_correct:
            print("✅ Parfait!")
        else:
            print("❌ Réponse incorrecte.")
            if not french_correct:
                print(f"   Traduction     : {french}")
            if not preterit_correct:
                print(f"   Prétérit       : {preterit}")
            if not pp_correct:
                print(f"   Participe passé: {pp}")

        self.db.update_score(word_id, is_correct)
        return is_correct

    def check_basic_word(self, word_data: Tuple) -> bool:
        """
        Tester un mot basique : donné en français, répondre en anglais.
        """
        word_id, english, french, word_type, is_irregular, preterit, pp, correct, total = word_data  # Dépaquetage du tuple mot

        print(f"\n📝 Mot : {french}")
        user_answer = input("Traduction anglaise : ")

        is_correct = self.normalize_answer(user_answer) == self.normalize_answer(english)

        if is_correct:
            print("✅ Parfait!")
        else:
            print(f"❌ Réponse incorrecte. La bonne réponse était : {english}")

        self.db.update_score(word_id, is_correct)
        return is_correct

    def check_acronym(self, word_data: Tuple) -> bool:
        """
        Tester un acronyme : donné l'acronyme, répondre avec son sens.
        """
        word_id, english, french, word_type, is_irregular, preterit, pp, correct, total = word_data  # Dépaquetage du tuple mot

        print(f"\n📝 Acronyme : {english}")
        user_answer = input("Que signifie cet acronyme ? : ")

        is_correct = self.normalize_answer(user_answer) == self.normalize_answer(french)

        if is_correct:
            print("✅ Parfait!")
        else:
            print(f"❌ Réponse incorrecte. La bonne réponse était : {french}")

        self.db.update_score(word_id, is_correct)
        return is_correct

    def run_quiz(self, num_questions: int = 10, quiz_type: str = 'all'):
        """
        Lancer un quiz.
        quiz_type : 'verb', 'word', 'acronym', ou 'all'
        """
        type_labels = {
            'verb': 'Verbes irréguliers',
            'word': 'Mots basiques',
            'acronym': 'Acronymes',
            'all': 'Tous types mélangés'
        }
        label = type_labels.get(quiz_type, 'Quiz')  # Libellé affiché dans le titre du quiz

        print(f"\n🎯 Quiz — {label} — {num_questions} questions\n")
        print("=" * 50)

        correct_count = 0  # Compteur de bonnes réponses pour le score final

        for i in range(num_questions):
            wtype = None if quiz_type == 'all' else quiz_type  # None = pas de filtre par type
            word_data = self.db.get_word_for_quiz(word_type=wtype)

            if not word_data:
                print(f"❌ Aucun mot de type '{quiz_type}' dans la base de données!")
                break

            print(f"\n📊 Question {i + 1}/{num_questions}")

            wt = word_data[3]  # Index 3 = word_type dans le tuple retourné par la BDD

            if wt == 'verb':
                result = self.check_irregular_verb(word_data)
            elif wt == 'acronym':
                result = self.check_acronym(word_data)
            else:
                result = self.check_basic_word(word_data)  # Par défaut : mot basique

            if result:
                correct_count += 1

        print("\n" + "=" * 50)
        print(f"🏆 Résultats: {correct_count}/{num_questions} ({correct_count / num_questions * 100:.1f}%)")
        print("=" * 50)


class VocabularyApp:
    """Application principale"""

    def __init__(self):
        self.db = VocabularyDatabase()  # Initialise (ou ouvre) la base de données
        self.quiz = VocabularyQuiz(self.db)  # Injecte la BDD dans le moteur de quiz

    def display_menu(self):
        """Afficher le menu principal"""
        print("\n" + "=" * 60)
        print("📚 APPLICATION D'APPRENTISSAGE DU VOCABULAIRE ANGLAIS")
        print("=" * 60)
        print("\n1. Ajouter un mot")
        print("2. Modifier un mot")
        print("3. Supprimer un mot")
        print("4. Afficher tous les mots")
        print("5. Rechercher un mot")
        print("6. Lancer un quiz")
        print("7. Afficher les statistiques")
        print("8. Réinitialisation des mots par défaut")
        print("0. Quitter")
        print("-" * 60)

    # ------------------------------------------------------------------ #
    #  OPTION 1 — Ajouter un mot (nouveau sous-menu)                      #
    # ------------------------------------------------------------------ #
    def add_word_interactive(self):
        """Sous-menu pour choisir le type de mot à ajouter"""
        print("\n➕ AJOUTER — Quel type ?")
        print("-" * 40)
        print("1. Verbe irrégulier")
        print("2. Mot basique")
        print("3. Acronyme")
        print("0. Retour")
        print("-" * 40)

        choice = input("Votre choix : ").strip()

        if choice == '1':
            self._add_verb()
        elif choice == '2':
            self._add_basic_word()
        elif choice == '3':
            self._add_acronym()
        elif choice == '0':
            return  # Retour au menu principal sans action
        else:
            print("❌ Choix invalide.")

    def _add_verb(self):
        """Ajouter un verbe irrégulier"""
        print("\n📝 AJOUTER UN VERBE IRRÉGULIER")
        print("-" * 40)
        english = input("Verbe (infinitif anglais) : ").strip()
        french = input("Traduction française       : ").strip()
        preterit = input("Prétérit                  : ").strip()
        past_participle = input("Participe passé           : ").strip()

        if self.db.add_word(english, french, word_type='verb',
                            is_irregular=True,
                            preterit=preterit, past_participle=past_participle):
            print("✅ Verbe ajouté avec succès!")
        else:
            print("❌ Échec de l'ajout.")

    def _add_basic_word(self):
        """Ajouter un mot basique (FR → EN)"""
        print("\n📝 AJOUTER UN MOT BASIQUE")
        print("-" * 40)
        french = input("Mot en français  : ").strip()
        english = input("Traduction anglaise : ").strip()

        if self.db.add_word(english, french, word_type='word'):
            print("✅ Mot ajouté avec succès!")
        else:
            print("❌ Échec de l'ajout.")

    def _add_acronym(self):
        """Ajouter un acronyme"""
        print("\n📝 AJOUTER UN ACRONYME")
        print("-" * 40)
        acronym = input("Acronyme (ex: NATO, HTML...) : ").strip().upper()  # Forcé en majuscules
        meaning = input("Signification complète       : ").strip()

        if self.db.add_word(acronym, meaning, word_type='acronym'):
            print("✅ Acronyme ajouté avec succès!")
        else:
            print("❌ Échec de l'ajout.")

    # ------------------------------------------------------------------ #
    #  OPTION 2 — Modifier un mot                                         #
    # ------------------------------------------------------------------ #
    def modify_word_interactive(self):
        """Modifier un mot de façon interactive"""
        print("\n✏️  MODIFIER UN MOT")
        print("-" * 40)

        search = input("Rechercher le mot à modifier: ")
        results = self.db.search_word(search)

        if not results:
            print("❌ Aucun mot trouvé.")
            return

        print("\nRésultats:")
        for word in results:
            self.display_word_info(word)

        try:
            word_id = int(input("\nID du mot à modifier: "))
        except ValueError:  # Saisie non numérique : abandon
            print("❌ ID invalide.")
            return

        print("\nLaissez vide pour conserver la valeur actuelle.")
        english = input("Nouveau mot / acronyme anglais : ").strip() or None  # Entrée vide → None → update_word conservera la valeur actuelle
        french = input("Nouvelle traduction / signification : ").strip() or None
        preterit = input("Nouveau prétérit (verbes seulement): ").strip() or None
        past_participle = input("Nouveau participe passé (verbes seulement): ").strip() or None

        if self.db.update_word(word_id, english, french,
                               preterit=preterit, past_participle=past_participle):
            print("✅ Mot modifié avec succès!")
        else:
            print("❌ Échec de la modification.")

    # ------------------------------------------------------------------ #
    #  OPTION 3 — Supprimer                                               #
    # ------------------------------------------------------------------ #
    def delete_word_interactive(self):
        """Supprimer un mot de façon interactive"""
        print("\n🗑️  SUPPRIMER UN MOT")
        print("-" * 40)

        search = input("Rechercher le mot à supprimer: ")
        results = self.db.search_word(search)

        if not results:
            print("❌ Aucun mot trouvé.")
            return

        print("\nRésultats:")
        for word in results:
            self.display_word_info(word)

        try:
            word_id = int(input("\nID du mot à supprimer: "))
        except ValueError:  # Saisie non numérique : abandon
            print("❌ ID invalide.")
            return

        confirm = input("Confirmer la suppression? (o/n): ").lower()

        if confirm == 'o':  # Sécurité : confirmation explicite avant suppression irréversible
            if self.db.delete_word(word_id):
                print("✅ Mot supprimé avec succès!")
            else:
                print("❌ Échec de la suppression.")

    # ------------------------------------------------------------------ #
    #  Affichage                                                           #
    # ------------------------------------------------------------------ #
    def display_word_info(self, word: Tuple):
        """Afficher les informations d'un mot en format tableau"""
        word_id, english, french, word_type, is_irregular, preterit, pp, correct, total = word  # Dépaquetage du tuple mot

        success_rate = (correct / total * 100) if total > 0 else 0  # Évite division par zéro
        score = f"{correct}/{total} ({success_rate:.0f}%)"

        if word_type == 'verb':
            print(f"  {word_id:<4} | {english:<20} | {french:<25} | {str(preterit):<15} | {str(pp):<15} | {score}")
        elif word_type == 'acronym':
            print(f"  {word_id:<4} | {english:<10} | {french:<45} | {score}")
        else:
            print(f"  {word_id:<4} | {french:<20} | {english:<35} | {score}")

    def display_all_words(self):
        """Afficher tous les mots en tableau par section"""
        print("\n📚 LISTE DES MOTS")
        print("=" * 90)

        words = self.db.get_all_words()

        if not words:
            print("❌ Aucun mot dans la base de données.")
            return

        current_type = None  # Mémorise le type en cours pour détecter les changements de section
        section_labels = {'verb': '🔄 VERBES IRRÉGULIERS', 'word': '📖 MOTS BASIQUES', 'acronym': '🔤 ACRONYMES'}
        headers = {
            'verb':    f"  {'ID':<4} | {'Anglais':<20} | {'Français':<25} | {'Prétérit':<15} | {'Participe passé':<15} | Score",
            'word':    f"  {'ID':<4} | {'Français':<20} | {'Anglais':<35} | Score",
            'acronym': f"  {'ID':<4} | {'Acronyme':<10} | {'Signification':<45} | Score",
        }

        for word in words:
            wtype = word[3]  # Index 3 = word_type
            if wtype != current_type:  # Changement de section → affiche un séparateur et l'en-tête
                current_type = wtype
                print(f"\n{'─' * 90}")
                print(f"  {section_labels.get(wtype, wtype.upper())}")
                print(f"{'─' * 90}")
                print(headers.get(wtype, ''))
                print(f"{'─' * 90}")
            self.display_word_info(word)

        print("\n" + "=" * 90)
        print(f"Total: {len(words)} entrées")

    def search_word_interactive(self):
        """Rechercher un mot de façon interactive"""
        print("\n🔍 RECHERCHER UN MOT")
        print("-" * 40)

        search = input("Terme de recherche: ")
        results = self.db.search_word(search)

        if not results:
            print("❌ Aucun résultat trouvé.")
            return

        print(f"\n✅ {len(results)} résultat(s) trouvé(s):")
        for word in results:
            self.display_word_info(word)

    # ------------------------------------------------------------------ #
    #  OPTION 6 — Quiz (sous-menu par type)                               #
    # ------------------------------------------------------------------ #
    def run_quiz_interactive(self):
        """Choisir le type de quiz puis le lancer"""
        print("\n🎯 CHOISIR LE TYPE DE QUIZ")
        print("-" * 40)
        print("1. Verbes irréguliers")
        print("2. Mots basiques")
        print("3. Acronymes")
        print("4. Tout mélanger")
        print("0. Retour")
        print("-" * 40)

        choice = input("Votre choix : ").strip()

        type_map = {'1': 'verb', '2': 'word', '3': 'acronym', '4': 'all'}  # Mapping choix → identifiant interne

        if choice == '0':
            return
        if choice not in type_map:
            print("❌ Choix invalide.")
            return

        try:
            num_questions = int(input("Nombre de questions (défaut: 10): ") or "10")
        except ValueError:
            num_questions = 10  # Valeur par défaut si saisie invalide

        self.quiz.run_quiz(num_questions, quiz_type=type_map[choice])

    # ------------------------------------------------------------------ #
    #  OPTION 7 — Statistiques                                            #
    # ------------------------------------------------------------------ #
    def display_statistics(self):
        """Afficher les statistiques"""
        stats = self.db.get_statistics()

        print("\n📊 STATISTIQUES GLOBALES")
        print("=" * 60)
        print(f"📚 Total d'entrées    : {stats['total_words']}")
        print(f"  🔄 Verbes           : {stats['verbs']}")
        print(f"  📖 Mots basiques    : {stats['basic_words']}")
        print(f"  🔤 Acronymes        : {stats['acronyms']}")
        print(f"📝 Tentatives totales : {stats['total_attempts']}")
        print(f"✅ Réponses correctes : {stats['correct_answers']}")
        print(f"🎯 Taux de réussite   : {stats['success_rate']:.1f}%")
        print("=" * 60)

    # ------------------------------------------------------------------ #
    #  OPTION 8 — Mots par défaut                                         #
    # ------------------------------------------------------------------ #
    def add_sample_words(self):
        """Ajouter des mots d'exemple"""
        print("\n➕ Ajout de mots d'exemple...")

        sample_words = [
            # (english, french, word_type, is_irregular, preterit, past_participle)

            # Mots basiques — sens FR → EN dans le quiz
            ("house", "maison", "word", False, None, None),
            ("cat", "chat", "word", False, None, None),
            ("book", "livre", "word", False, None, None),
            ("water", "eau", "word", False, None, None),
            ("tree", "arbre", "word", False, None, None),
            ("car", "voiture", "word", False, None, None),
            ("dog", "chien", "word", False, None, None),
            ("table", "table", "word", False, None, None),
            ("chair", "chaise", "word", False, None, None),
            ("window", "fenêtre", "word", False, None, None),
            ("door", "porte", "word", False, None, None),
            ("friend", "ami", "word", False, None, None),
            ("family", "famille", "word", False, None, None),
            ("school", "école", "word", False, None, None),
            ("computer", "ordinateur", "word", False, None, None),
            ("phone", "téléphone", "word", False, None, None),
            ("food", "nourriture", "word", False, None, None),
            ("money", "argent", "word", False, None, None),
            ("time", "temps", "word", False, None, None),
            ("day", "jour", "word", False, None, None),
            ("night", "nuit", "word", False, None, None),
            ("sun", "soleil", "word", False, None, None),
            ("moon", "lune", "word", False, None, None),
            ("star", "étoile", "word", False, None, None),
            ("city", "ville", "word", False, None, None),
            ("country", "pays", "word", False, None, None),
            ("world", "monde", "word", False, None, None),
            ("music", "musique", "word", False, None, None),
            ("movie", "film", "word", False, None, None),
            ("game", "jeu", "word", False, None, None),

            # Verbes irréguliers
            ("go", "aller", "verb", True, "went", "gone"),
            ("see", "voir", "verb", True, "saw", "seen"),
            ("do", "faire", "verb", True, "did", "done"),
            ("have", "avoir", "verb", True, "had", "had"),
            ("be", "être", "verb", True, "was/were", "been"),
            ("take", "prendre", "verb", True, "took", "taken"),
            ("give", "donner", "verb", True, "gave", "given"),
            ("make", "faire/fabriquer", "verb", True, "made", "made"),
            ("come", "venir", "verb", True, "came", "come"),
            ("think", "penser", "verb", True, "thought", "thought"),
            ("know", "savoir/connaître", "verb", True, "knew", "known"),
            ("get", "obtenir", "verb", True, "got", "got/gotten"),
            ("find", "trouver", "verb", True, "found", "found"),
            ("tell", "dire/raconter", "verb", True, "told", "told"),
            ("become", "devenir", "verb", True, "became", "become"),
            ("leave", "partir/quitter", "verb", True, "left", "left"),
            ("feel", "sentir/ressentir", "verb", True, "felt", "felt"),
            ("bring", "apporter", "verb", True, "brought", "brought"),
            ("begin", "commencer", "verb", True, "began", "begun"),
            ("keep", "garder", "verb", True, "kept", "kept"),
            ("hold", "tenir", "verb", True, "held", "held"),
            ("write", "écrire", "verb", True, "wrote", "written"),
            ("stand", "se tenir debout", "verb", True, "stood", "stood"),
            ("hear", "entendre", "verb", True, "heard", "heard"),
            ("let", "laisser/permettre", "verb", True, "let", "let"),
            ("mean", "signifier", "verb", True, "meant", "meant"),
            ("set", "placer/fixer", "verb", True, "set", "set"),
            ("meet", "rencontrer", "verb", True, "met", "met"),
            ("run", "courir", "verb", True, "ran", "run"),
            ("pay", "payer", "verb", True, "paid", "paid"),
            ("sit", "s'asseoir", "verb", True, "sat", "sat"),
            ("speak", "parler", "verb", True, "spoke", "spoken"),
            ("lie", "mentir", "verb", True, "lay", "lain"),
            ("lead", "mener/diriger", "verb", True, "led", "led"),
            ("read", "lire", "verb", True, "read", "read"),
            ("grow", "grandir/pousser", "verb", True, "grew", "grown"),
            ("lose", "perdre", "verb", True, "lost", "lost"),
            ("fall", "tomber", "verb", True, "fell", "fallen"),
            ("send", "envoyer", "verb", True, "sent", "sent"),
            ("build", "construire", "verb", True, "built", "built"),
            ("understand", "comprendre", "verb", True, "understood", "understood"),
            ("draw", "dessiner", "verb", True, "drew", "drawn"),
            ("break", "casser", "verb", True, "broke", "broken"),
            ("spend", "dépenser", "verb", True, "spent", "spent"),
            ("cut", "couper", "verb", True, "cut", "cut"),
            ("rise", "se lever/monter", "verb", True, "rose", "risen"),
            ("drive", "conduire", "verb", True, "drove", "driven"),
            ("buy", "acheter", "verb", True, "bought", "bought"),
            ("wear", "porter (vêtement)", "verb", True, "wore", "worn"),
            ("choose", "choisir", "verb", True, "chose", "chosen"),
            ("seek", "chercher", "verb", True, "sought", "sought"),
            ("throw", "jeter", "verb", True, "threw", "thrown"),
            ("catch", "attraper", "verb", True, "caught", "caught"),
            ("fly", "voler", "verb", True, "flew", "flown"),
            ("forget", "oublier", "verb", True, "forgot", "forgotten"),
            ("hide", "cacher", "verb", True, "hid", "hidden"),
            ("ring", "sonner", "verb", True, "rang", "rung"),
            ("sing", "chanter", "verb", True, "sang", "sung"),
            ("swim", "nager", "verb", True, "swam", "swum"),
            ("teach", "enseigner", "verb", True, "taught", "taught"),
            ("win", "gagner", "verb", True, "won", "won"),

            # Acronymes d'exemple
            ("NATO", "North Atlantic Treaty Organization", "acronym", False, None, None),
            ("HTML", "HyperText Markup Language", "acronym", False, None, None),
            ("CSS", "Cascading Style Sheets", "acronym", False, None, None),
            ("SQL", "Structured Query Language", "acronym", False, None, None),
            ("API", "Application Programming Interface", "acronym", False, None, None),
            ("URL", "Uniform Resource Locator", "acronym", False, None, None),
            ("PDF", "Portable Document Format", "acronym", False, None, None),
            ("GPS", "Global Positioning System", "acronym", False, None, None),
            ("USB", "Universal Serial Bus", "acronym", False, None, None),
            ("AI", "Artificial Intelligence", "acronym", False, None, None),
        ]

        added = 0
        for word_data in sample_words:
            english, french, word_type, is_irregular, preterit, pp = word_data  # Dépaquetage du tuple
            if self.db.add_word(english, french, word_type=word_type,
                                is_irregular=is_irregular,
                                preterit=preterit, past_participle=pp):
                added += 1  # Comptabilise uniquement les ajouts réussis (non-doublons)

        print(f"✅ {added} entrées d'exemple ajoutées!")

    # ------------------------------------------------------------------ #
    #  Boucle principale                                                   #
    # ------------------------------------------------------------------ #
    def run(self):
        """Lancer l'application"""
        while True:  # Boucle principale : tourne jusqu'à ce que l'utilisateur choisisse 0
            self.display_menu()

            choice = input("\nVotre choix: ").strip()

            if choice == '1':
                self.add_word_interactive()
            elif choice == '2':
                self.modify_word_interactive()
            elif choice == '3':
                self.delete_word_interactive()
            elif choice == '4':
                self.display_all_words()
            elif choice == '5':
                self.search_word_interactive()
            elif choice == '6':
                self.run_quiz_interactive()
            elif choice == '7':
                self.display_statistics()
            elif choice == '8':
                self.add_sample_words()
            elif choice == '0':
                print("\n👋 Au revoir!")
                self.db.close()
                break  # Quitte la boucle et termine le programme
            else:
                print("❌ Choix invalide.")

            input("\nAppuyez sur Entrée pour continuer...")


if __name__ == "__main__":
    app = VocabularyApp()
    app.run()  # Point d'entrée : lance l'application uniquement si exécuté directement (pas importé)
