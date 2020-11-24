from re import match

from pymongo import MongoClient
from flask import Flask, request, render_template

db = MongoClient("mongodb://localhost:27017")["airnic"]
app = Flask(__name__)

AIRNIC_TLDS = ["air", "ham"]

regex_email = r"[^@]+@[^@]+\.[^@]+"
regex_domain = r"(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    else:
        query = request.form.get("query")
        if not query:
            return render_template("index.html", error="Query must not be empty")

        if "." in query:
            if query.endswith(tuple(AIRNIC_TLDS)):
                zones_result = db["zones"].find({"zone": query})
                return render_template("index.html", results={query: zones_result.count() == 0})
            else:
                return render_template("index.html", error="AirNIC is only authoritative for the .air and .ham TLDs")
        else:
            results = {}

            for tld in AIRNIC_TLDS:
                _exists = db["zones"].find({"zone": query + "." + tld})
                results[query + "." + tld] = _exists.count() == 0

            return render_template("index.html", results=results)


@app.route("/register/<domain>", methods=["GET", "POST"])
def register(domain):
    if not ("." in domain and domain.endswith(tuple(AIRNIC_TLDS))):
        return render_template("register.html", error="This is an error")

    if request.method == "GET":
        return render_template("index.html", register=domain)
    else:
        nameservers = request.form.get("nameservers").replace(" ", "").split(",")
        if len(nameservers) < 2:
            return render_template("index.html", error="You must set at least 2 nameservers. (Comma separated)")

        for ns in nameservers:
            if match(regex_domain, ns) is None:
                return render_template("index.html", error=f"Nameserver \"{ns}\" is invalid.")

        email = request.form.get("email")
        if email is None or (match(regex_email, email) is None):
            return render_template("index.html", error=f"Email \"{email}\" is invalid.")

        return "Done"


app.run(host="localhost", port=5000, debug=True)
