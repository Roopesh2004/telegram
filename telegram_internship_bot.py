# telegram_internship_bot.py

import os
import logging
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
import mysql.connector
from jinja2 import Template
import pdfkit

# --- Configure Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Telegram Bot Token ---
TELEGRAM_TOKEN = '7598613578:AAHzgxVt_ht7OcXvcGOlFbZtkVLinzWSIpk'  # Replace with your actual token

# --- Database Configuration (MySQL) ---
DB_CONFIG = {
    'host': 'srv1555.hstgr.io',
    'port': 3306,
    'user': 'u846003421_roopesh',
    'password': 'Roopesh@408719',
    'database': 'u846003421_interns'
}


# --- Get MySQL Connection ---
def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None


# --- Fetch Intern by Unique Code ---
def get_intern_by_code(code):
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, course_code, problem_statement FROM interns WHERE unique_code=%s", (code,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return {'name': row[0], 'course_code': row[1], 'problem_statement': row[2]}
    except Exception as e:
        logger.error(f"Error fetching intern: {e}")
    return None


# --- Save GitHub Repo ---
def save_repo(code, repo):
    conn = get_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE interns SET github_link=%s WHERE unique_code=%s", (repo, code))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving repo: {e}")


# --- Generate Certificate as PDF ---
def generate_certificate(code):
    intern = get_intern_by_code(code)
    if not intern:
        logger.error(f"No intern found for code: {code}")
        return

    try:
        with open("certificate_template.html") as f:
            template_html = f.read()

        html = Template(template_html).render(
            name=intern["name"],
            course=intern["course_code"],
            date=datetime.now().strftime("%d-%m-%Y")
        )

        os.makedirs("certificates", exist_ok=True)
        cert_path = f"certificates/{code}.pdf"
        pdfkit.from_string(html, cert_path)
    except Exception as e:
        logger.error(f"Certificate generation error: {e}")


# --- Command: /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the Internship Bot!\nUse /verify <your_code> to begin.")


# --- Command: /verify ---
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        return await update.message.reply_text("⚠️ Usage: /verify <your_code>")

    code = context.args[0].strip()
    logger.info(f"/verify command from {update.effective_user.id} for code: {code}")
    intern = get_intern_by_code(code)

    if intern:
        context.user_data['code'] = code
        await update.message.reply_text(
            f"✅ Verified!\n👤 Name: {intern['name']}\n📘 Course: {intern['course_code']}\n💡 Problem: {intern['problem_statement']}\n\nSubmit repo using:\n/submit <github_link>"
        )
    else:
        await update.message.reply_text("❌ Invalid code. Please try again.")


# --- Command: /submit ---
async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'code' not in context.user_data:
        return await update.message.reply_text("❗ Please verify first using /verify <code>")

    if len(context.args) != 1:
        return await update.message.reply_text("⚠️ Usage: /submit <github_repo_link>")

    code = context.user_data['code']
    repo = context.args[0].strip()

    save_repo(code, repo)
    generate_certificate(code)
    await update.message.reply_text("✅ GitHub link submitted and certificate generated!")


# --- Command: /certificate ---
async def certificate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = context.user_data.get('code')
    if not code:
        return await update.message.reply_text("❗ Please verify first using /verify <code>")

    cert_path = f"certificates/{code}.pdf"
    if os.path.exists(cert_path):
        await update.message.reply_document(open(cert_path, 'rb'))
    else:
        await update.message.reply_text("❌ Certificate not found or not yet generated.")


# --- Main Function ---
def main():
    logger.info("🚀 Starting bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verify", verify))
    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(CommandHandler("certificate", certificate))

    app.run_polling()


if __name__ == '__main__':
    main()
