#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application d'apprentissage du vocabulaire anglais
Avec gestion des verbes irréguliers et système de scoring intelligent
"""

import sqlite3
import random
from datetime import datetime
from typing import Optional, List, Tuple
#import os ( pas utiliser pour l'instant )

# Programme organiser en 3 classes
# -VocabularyDatabase
# -VocabularyQuiz
# -VocabularyApp
class VocabularyDatabase:
    """Gestion de la base de données de vocabulaire"""
    
    def __init__(self, db_name: str = "vocabulary.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Connexion à la base de données"""
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
    
    def create_tables(self):
        """Création des tables si elles n'existent pas"""
        # Table des mots
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english TEXT NOT NULL UNIQUE,
                french TEXT NOT NULL,
                is_irregular_verb INTEGER DEFAULT 0,
                preterit TEXT,
                past_participle TEXT,
                correct_answers INTEGER DEFAULT 0,
                total_attempts INTEGER DEFAULT 0,
                last_tested TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def add_word(self, english: str, french: str, is_irregular: bool = False,
                 preterit: Optional[str] = None, past_participle: Optional[str] = None) -> bool:
        """Ajouter un mot à la base de données"""
        try:
            self.cursor.execute('''
                INSERT INTO words (english, french, is_irregular_verb, preterit, past_participle)
                VALUES (?, ?, ?, ?, ?)
            ''', (english.lower().strip(), french.strip(), 
                  1 if is_irregular else 0, 
                  preterit.lower().strip() if preterit else None,
                  past_participle.lower().strip() if past_participle else None))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"⚠️  Le mot '{english}' existe déjà dans la base de données.")
            return False
    
    def update_word(self, word_id: int, english: Optional[str] = None, 
                   french: Optional[str] = None, is_irregular: Optional[bool] = None,
                   preterit: Optional[str] = None, past_participle: Optional[str] = None) -> bool:
        """Modifier un mot existant"""
        # Récupérer les valeurs actuelles
        self.cursor.execute('SELECT * FROM words WHERE id = ?', (word_id,))
        current = self.cursor.fetchone()
        
        if not current:
            print(f"❌ Aucun mot trouvé avec l'ID {word_id}")
            return False
        
        # Utiliser les valeurs actuelles si non spécifiées
        english = english if english is not None else current[1]
        french = french if french is not None else current[2]
        is_irregular = (1 if is_irregular else 0) if is_irregular is not None else current[3]
        preterit = preterit if preterit is not None else current[4]
        past_participle = past_participle if past_participle is not None else current[5]
        
        try:
            self.cursor.execute('''
                UPDATE words 
                SET english = ?, french = ?, is_irregular_verb = ?, 
                    preterit = ?, past_participle = ?
                WHERE id = ?
            ''', (english.lower().strip(), french.strip(), is_irregular,
                  preterit.lower().strip() if preterit else None,
                  past_participle.lower().strip() if past_participle else None,
                  word_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"⚠️  Le mot '{english}' existe déjà.")
            return False
    
    def delete_word(self, word_id: int) -> bool:
        """Supprimer un mot"""
        self.cursor.execute('DELETE FROM words WHERE id = ?', (word_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_all_words(self) -> List[Tuple]:
        """Récupérer tous les mots"""
        self.cursor.execute('''
            SELECT id, english, french, is_irregular_verb, preterit, past_participle,
                   correct_answers, total_attempts
            FROM words
            ORDER BY english
        ''')
        return self.cursor.fetchall()
    
    def search_word(self, search_term: str) -> List[Tuple]:
        """Rechercher un mot"""
        self.cursor.execute('''
            SELECT id, english, french, is_irregular_verb, preterit, past_participle,
                   correct_answers, total_attempts
            FROM words
            WHERE english LIKE ? OR french LIKE ?
            ORDER BY english
        ''', (f'%{search_term}%', f'%{search_term}%'))
        return self.cursor.fetchall()
    
    def get_word_for_quiz(self) -> Optional[Tuple]:
        """
        Sélectionner un mot pour le quiz en privilégiant les mots avec faible taux de réussite
        Utilise un système de pondération basé sur le taux d'échec
        """
        self.cursor.execute('''
            SELECT id, english, french, is_irregular_verb, preterit, past_participle,
                   correct_answers, total_attempts
            FROM words
        ''')
        words = self.cursor.fetchall()
        
        if not words:
            return None
        
        # Calculer les poids pour chaque mot
        weighted_words = []
        for word in words:
            word_id, english, french, is_irregular, preterit, pp, correct, total = word
            
            # Calculer le taux de réussite
            if total == 0:
                # Les mots jamais testés ont un poids maximal
                weight = 100
            else:
                success_rate = correct / total
                # Poids inversement proportionnel au taux de réussite
                # Plus le taux est faible, plus le poids est élevé
                weight = max(1, int((1 - success_rate) * 100))
            
            weighted_words.append((word, weight))
        
        # Sélection pondérée
        total_weight = sum(w[1] for w in weighted_words)
        rand_val = random.randint(1, total_weight)
        
        cumulative = 0
        for word, weight in weighted_words:
            cumulative += weight
            if rand_val <= cumulative:
                return word
        
        return weighted_words[-1][0]
    
    def update_score(self, word_id: int, is_correct: bool):
        """Mettre à jour le score d'un mot"""
        self.cursor.execute('''
            UPDATE words
            SET correct_answers = correct_answers + ?,
                total_attempts = total_attempts + 1,
                last_tested = ?
            WHERE id = ?
        ''', (1 if is_correct else 0, datetime.now(), word_id))
        self.conn.commit()
    
    def get_statistics(self) -> dict:
        """Obtenir les statistiques globales"""
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total_words,
                SUM(is_irregular_verb) as irregular_verbs,
                SUM(total_attempts) as total_attempts,
                SUM(correct_answers) as correct_answers
            FROM words
        ''')
        row = self.cursor.fetchone()
        
        total_words, irregular_verbs, total_attempts, correct_answers = row
        
        return {
            'total_words': total_words or 0,
            'irregular_verbs': irregular_verbs or 0,
            'total_attempts': total_attempts or 0,
            'correct_answers': correct_answers or 0,
            'success_rate': (correct_answers / total_attempts * 100) if total_attempts > 0 else 0
        }
    
    def close(self):
        """Fermer la connexion"""
        if self.conn:
            self.conn.close()


class VocabularyQuiz:
    """Gestion du quiz de vocabulaire"""
    
    def __init__(self, db: VocabularyDatabase):
        self.db = db
    
    def normalize_answer(self, answer: str) -> str:
        """Normaliser une réponse"""
        return answer.lower().strip()
    
    def check_translation(self, word_data: Tuple) -> bool:
        """Tester la traduction d'un mot"""
        word_id, english, french, is_irregular, preterit, pp, correct, total = word_data
        
        print(f"\n📝 Traduisez: {english}")
        user_answer = input("Votre réponse: ")
        
        is_correct = self.normalize_answer(user_answer) == self.normalize_answer(french)
        
        if is_correct:
            print("✅ Correct!")
        else:
            print(f"❌ Incorrect. La bonne réponse est: {french}")
        
        self.db.update_score(word_id, is_correct)
        return is_correct
    
    def check_irregular_verb(self, word_data: Tuple) -> bool:
        """Tester le prétérit et participe passé d'un verbe irrégulier"""
        word_id, english, french, is_irregular, preterit, pp, correct, total = word_data
        
        print(f"\n📝 Verbe irrégulier: {english} ({french})")
        print("Donnez le prétérit et le participe passé:")
        
        user_preterit = input("Prétérit: ")
        user_pp = input("Participe passé: ")
        
        preterit_correct = self.normalize_answer(user_preterit) == self.normalize_answer(preterit)
        pp_correct = self.normalize_answer(user_pp) == self.normalize_answer(pp)
        
        is_correct = preterit_correct and pp_correct
        
        if is_correct:
            print("✅ Parfait!")
        else:
            print(f"❌ Réponse incorrecte.")
            if not preterit_correct:
                print(f"   Prétérit: {preterit}")
            if not pp_correct:
                print(f"   Participe passé: {pp}")
        
        self.db.update_score(word_id, is_correct)
        return is_correct
    
    def run_quiz(self, num_questions: int = 10):
        """Lancer un quiz"""
        print(f"\n🎯 Quiz de {num_questions} questions\n")
        print("=" * 50)
        
        correct_count = 0
        
        for i in range(num_questions):
            word_data = self.db.get_word_for_quiz()
            
            if not word_data:
                print("❌ Aucun mot dans la base de données!")
                break
            
            print(f"\n📊 Question {i + 1}/{num_questions}")
            
            is_irregular = word_data[3]
            
            if is_irregular:
                is_correct = self.check_irregular_verb(word_data)
            else:
                is_correct = self.check_translation(word_data)
            
            if is_correct:
                correct_count += 1
        
        # Résultats
        print("\n" + "=" * 50)
        print(f"🏆 Résultats: {correct_count}/{num_questions} ({correct_count/num_questions*100:.1f}%)")
        print("=" * 50)


class VocabularyApp:
    """Application principale"""
    
    def __init__(self):
        self.db = VocabularyDatabase()
        self.quiz = VocabularyQuiz(self.db)
    
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
    
    def add_word_interactive(self):
        """Ajouter un mot de façon interactive"""
        print("\n➕ AJOUTER UN MOT")
        print("-" * 40)
        
        english = input("Mot en anglais: ").strip()
        french = input("Traduction française: ").strip()
        
        is_irregular = input("Est-ce un verbe irrégulier? (o/n): ").lower() == 'o'
        
        preterit = None
        past_participle = None
        
        if is_irregular:
            preterit = input("Prétérit: ").strip()
            past_participle = input("Participe passé: ").strip()
        
        if self.db.add_word(english, french, is_irregular, preterit, past_participle):
            print("✅ Mot ajouté avec succès!")
        else:
            print("❌ Échec de l'ajout du mot.")
    
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
        except ValueError:
            print("❌ ID invalide.")
            return
        
        print("\nLaissez vide pour conserver la valeur actuelle.")
        english = input("Nouveau mot anglais: ").strip() or None
        french = input("Nouvelle traduction: ").strip() or None
        
        is_irregular_input = input("Verbe irrégulier? (o/n/vide): ").lower()
        is_irregular = True if is_irregular_input == 'o' else (False if is_irregular_input == 'n' else None)
        
        preterit = input("Nouveau prétérit: ").strip() or None
        past_participle = input("Nouveau participe passé: ").strip() or None
        
        if self.db.update_word(word_id, english, french, is_irregular, preterit, past_participle):
            print("✅ Mot modifié avec succès!")
        else:
            print("❌ Échec de la modification.")
    
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
        except ValueError:
            print("❌ ID invalide.")
            return
        
        confirm = input(f"Confirmer la suppression? (o/n): ").lower()
        
        if confirm == 'o':
            if self.db.delete_word(word_id):
                print("✅ Mot supprimé avec succès!")
            else:
                print("❌ Échec de la suppression.")
    
    def display_word_info(self, word: Tuple):
        """Afficher les informations d'un mot"""
        word_id, english, french, is_irregular, preterit, pp, correct, total = word
        
        success_rate = (correct / total * 100) if total > 0 else 0
        
        print(f"\n  ID: {word_id}")
        print(f"  📖 {english} → {french}")
        
        if is_irregular:
            print(f"  🔄 Verbe irrégulier: {preterit} / {pp}")
        
        print(f"  📊 Score: {correct}/{total} ({success_rate:.1f}%)")
    
    def display_all_words(self):
        """Afficher tous les mots"""
        print("\n📚 LISTE DES MOTS")
        print("=" * 60)
        
        words = self.db.get_all_words()
        
        if not words:
            print("❌ Aucun mot dans la base de données.")
            return
        
        for word in words:
            self.display_word_info(word)
        
        print("\n" + "=" * 60)
        print(f"Total: {len(words)} mots")
    
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
    
    def display_statistics(self):
        """Afficher les statistiques"""
        stats = self.db.get_statistics()
        
        print("\n📊 STATISTIQUES GLOBALES")
        print("=" * 60)
        print(f"📚 Total de mots: {stats['total_words']}")
        print(f"🔄 Verbes irréguliers: {stats['irregular_verbs']}")
        print(f"📝 Tentatives totales: {stats['total_attempts']}")
        print(f"✅ Réponses correctes: {stats['correct_answers']}")
        print(f"🎯 Taux de réussite global: {stats['success_rate']:.1f}%")
        print("=" * 60)
    
    def add_sample_words(self):
        """Ajouter des mots d'exemple"""
        print("\n➕ Ajout de mots d'exemple...")
        
        sample_words = [
            # Mots réguliers
            ("house", "maison", False, None, None),
            ("cat", "chat", False, None, None),
            ("book", "livre", False, None, None),
            ("water", "eau", False, None, None),
            ("tree", "arbre", False, None, None),
            ("car", "voiture", False, None, None),
            ("dog", "chien", False, None, None),
            ("table", "table", False, None, None),
            ("chair", "chaise", False, None, None),
            ("window", "fenêtre", False, None, None),
            ("door", "porte", False, None, None),
            ("friend", "ami", False, None, None),
            ("family", "famille", False, None, None),
            ("school", "école", False, None, None),
            ("computer", "ordinateur", False, None, None),
            ("phone", "téléphone", False, None, None),
            ("food", "nourriture", False, None, None),
            ("money", "argent", False, None, None),
            ("time", "temps", False, None, None),
            ("day", "jour", False, None, None),
            ("night", "nuit", False, None, None),
            ("sun", "soleil", False, None, None),
            ("moon", "lune", False, None, None),
            ("star", "étoile", False, None, None),
            ("city", "ville", False, None, None),
            ("country", "pays", False, None, None),
            ("world", "monde", False, None, None),
            ("music", "musique", False, None, None),
            ("movie", "film", False, None, None),
            ("game", "jeu", False, None, None),
            
            # Verbes irréguliers
            ("go", "aller", True, "went", "gone"),
            ("see", "voir", True, "saw", "seen"),
            ("do", "faire", True, "did", "done"),
            ("have", "avoir", True, "had", "had"),
            ("be", "être", True, "was/were", "been"),
            ("take", "prendre", True, "took", "taken"),
            ("give", "donner", True, "gave", "given"),
            ("make", "faire/fabriquer", True, "made", "made"),
            ("come", "venir", True, "came", "come"),
            ("think", "penser", True, "thought", "thought"),
            ("know", "savoir/connaître", True, "knew", "known"),
            ("get", "obtenir", True, "got", "got/gotten"),
            ("find", "trouver", True, "found", "found"),
            ("tell", "dire/raconter", True, "told", "told"),
            ("become", "devenir", True, "became", "become"),
            ("leave", "partir/quitter", True, "left", "left"),
            ("feel", "sentir/ressentir", True, "felt", "felt"),
            ("bring", "apporter", True, "brought", "brought"),
            ("begin", "commencer", True, "began", "begun"),
            ("keep", "garder", True, "kept", "kept"),
            ("hold", "tenir", True, "held", "held"),
            ("write", "écrire", True, "wrote", "written"),
            ("stand", "se tenir debout", True, "stood", "stood"),
            ("hear", "entendre", True, "heard", "heard"),
            ("let", "laisser/permettre", True, "let", "let"),
            ("mean", "signifier", True, "meant", "meant"),
            ("set", "placer/fixer", True, "set", "set"),
            ("meet", "rencontrer", True, "met", "met"),
            ("run", "courir", True, "ran", "run"),
            ("pay", "payer", True, "paid", "paid"),
            ("sit", "s'asseoir", True, "sat", "sat"),
            ("speak", "parler", True, "spoke", "spoken"),
            ("lie", "mentir", True, "lay", "lain"),
            ("lead", "mener/diriger", True, "led", "led"),
            ("read", "lire", True, "read", "read"),
            ("grow", "grandir/pousser", True, "grew", "grown"),
            ("lose", "perdre", True, "lost", "lost"),
            ("fall", "tomber", True, "fell", "fallen"),
            ("send", "envoyer", True, "sent", "sent"),
            ("build", "construire", True, "built", "built"),
            ("understand", "comprendre", True, "understood", "understood"),
            ("draw", "dessiner", True, "drew", "drawn"),
            ("break", "casser", True, "broke", "broken"),
            ("spend", "dépenser", True, "spent", "spent"),
            ("cut", "couper", True, "cut", "cut"),
            ("rise", "se lever/monter", True, "rose", "risen"),
            ("drive", "conduire", True, "drove", "driven"),
            ("buy", "acheter", True, "bought", "bought"),
            ("wear", "porter (vêtement)", True, "wore", "worn"),
            ("choose", "choisir", True, "chose", "chosen"),
            ("seek", "chercher", True, "sought", "sought"),
            ("throw", "jeter", True, "threw", "thrown"),
            ("catch", "attraper", True, "caught", "caught"),
            ("fly", "voler", True, "flew", "flown"),
            ("forget", "oublier", True, "forgot", "forgotten"),
            ("hide", "cacher", True, "hid", "hidden"),
            ("ring", "sonner", True, "rang", "rung"),
            ("sing", "chanter", True, "sang", "sung"),
            ("swim", "nager", True, "swam", "swum"),
            ("teach", "enseigner", True, "taught", "taught"),
            ("win", "gagner", True, "won", "won"),
        ]
        
        added = 0
        for word_data in sample_words:
            if self.db.add_word(*word_data):
                added += 1
        
        print(f"✅ {added} mots d'exemple ajoutés!")
    
    def run_quiz_interactive(self):
        """Lancer un quiz de façon interactive"""
        print("\n🎯 LANCER UN QUIZ")
        print("-" * 40)
        
        try:
            num_questions = int(input("Nombre de questions (défaut: 10): ") or "10")
        except ValueError:
            num_questions = 10
        
        self.quiz.run_quiz(num_questions)
    
    def run(self):
        """Lancer l'application"""
        while True:
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
                break
            else:
                print("❌ Choix invalide.")
            
            input("\nAppuyez sur Entrée pour continuer...")


if __name__ == "__main__":
    app = VocabularyApp()
    app.run()
