from re import match
from time import time

from flask import Flask, request, render_template
from jinja2 import Template
from pymongo import MongoClient

db = MongoClient("mongodb://localhost:27017")["airnic"]
app = Flask(__name__)

AIRNIC_TLDS = ["air", "ham"]

regex_email = r"[^@]+@[^@]+\.[^@]+"
regex_domain = r"(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)"

with open("templates/tld.j2", "r") as tld_template_file:
    tld_template = Template(tld_template_file.read())


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

        _exists = db["zones"].find({"zone": domain})
        if _exists.count() != 0:
            return render_template("index.html", error=f"Domain \"{domain}\" is taken.")

        db["zones"].insert_one({
            "zone": domain,
            "email": email,
            "nameservers": nameservers
        })

        # Update the zone file
        tld = domain.split(".")[-1]
        zones = db["zones"].find({"zone": {"$regex": tld + "$"}})
        with open("db." + tld, "w") as zone_file:
            zone_file.write(tld_template.render(zones=zones, serial=str(int(time()))))

        return render_template("index.html", error=f"Thank you for registering {domain}. It has been pointed to your nameservers and will be live in a few seconds.")


app.run(host="localhost", port=5000, debug=True)
