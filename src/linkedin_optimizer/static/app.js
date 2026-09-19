/* Front end for POST /analyze: build the profile payload from the form,
   render the report. No framework, no build step. */

(function () {
  "use strict";

  var form = document.getElementById("profile-form");
  var reportPanel = document.getElementById("report");
  var submitButton = document.getElementById("submit-button");
  var experiencesHost = document.getElementById("experiences");
  var educationsHost = document.getElementById("educations");
  var exportInput = document.getElementById("export-file");
  var importStatus = document.getElementById("import-status");

  var SEVERITY_LABEL = {
    critical: "حرج",
    warning: "تحذير",
    info: "ملاحظة",
    success: "جيد",
  };

  var EXAMPLE = {
    full_name: "Layla Haddad",
    headline: "Senior Backend Engineer | Payments infrastructure at scale | Python, Go, Kubernetes",
    about:
      "I build payment systems that stay up on the busiest day of the year. Last year I led the " +
      "migration that cut our checkout error rate from 1.9% to 0.2% while traffic tripled.\n\n" +
      "I spend most of my time on the boring parts that decide whether a platform survives growth: " +
      "idempotency, retries, reconciliation, and the observability that tells you which of the three " +
      "failed.\n\nEmail me at layla@example.com.",
    location: "Amman, Jordan",
    industry: "Financial Services",
    target_role: "backend engineer",
    target_keywords: "api, database, microservices, scalability, sql, caching",
    skills:
      "Python, Go, Microservices, PostgreSQL, SQL, Redis, Caching, Kubernetes, API Design, " +
      "Distributed Systems, Scalability, Observability, Terraform, CI/CD, Payments, Database Design",
    certifications: "AWS Certified Solutions Architect",
    languages: "Arabic, English",
    connections_count: 1200,
    recommendations_count: 4,
    featured_count: 2,
    custom_url: "linkedin.com/in/layla-haddad",
    has_photo: true,
    has_banner: true,
    experiences: [
      {
        title: "Senior Backend Engineer",
        company: "Northwind Pay",
        start_date: "2021-03",
        end_date: "",
        description:
          "- Led the microservices migration of the checkout API, cutting p99 latency from 900ms to 210ms.\n" +
          "- Designed the caching layer that absorbed a 3x traffic increase with no added database capacity.",
      },
    ],
    educations: [
      {
        school: "University of Jordan",
        degree: "BSc",
        field_of_study: "Computer Engineering",
        start_year: "2014",
        end_year: "2018",
      },
    ],
  };

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function field(labelText, name, value, placeholder) {
    var label = el("label");
    label.appendChild(el("span", null, labelText));
    var input = el("input");
    input.type = "text";
    input.dataset.field = name;
    input.value = value || "";
    if (placeholder) input.placeholder = placeholder;
    label.appendChild(input);
    return label;
  }

  function splitList(value) {
    return (value || "")
      .split(",")
      .map(function (item) { return item.trim(); })
      .filter(function (item) { return item.length > 0; });
  }

  /* ---------- repeatable entries ---------- */

  function addExperience(data) {
    data = data || {};
    var entry = el("div", "entry");
    entry.dataset.entry = "experience";

    var head = el("div", "entry-head");
    head.appendChild(el("strong", null, "منصب"));
    var remove = el("button", null, "حذف");
    remove.type = "button";
    remove.addEventListener("click", function () { entry.remove(); });
    head.appendChild(remove);
    entry.appendChild(head);

    var row1 = el("div", "row");
    row1.appendChild(field("المسمّى", "title", data.title));
    row1.appendChild(field("الشركة", "company", data.company));
    entry.appendChild(row1);

    var row2 = el("div", "row");
    row2.appendChild(field("تاريخ البدء", "start_date", data.start_date, "YYYY-MM"));
    row2.appendChild(field("تاريخ الانتهاء (اتركه فارغًا إن كان حاليًا)", "end_date", data.end_date));
    entry.appendChild(row2);

    var label = el("label");
    label.appendChild(el("span", null, "الوصف — سطر لكل إنجاز"));
    var textarea = el("textarea");
    textarea.dataset.field = "description";
    textarea.value = data.description || "";
    label.appendChild(textarea);
    entry.appendChild(label);

    experiencesHost.appendChild(entry);
  }

  function addEducation(data) {
    data = data || {};
    var entry = el("div", "entry");
    entry.dataset.entry = "education";

    var head = el("div", "entry-head");
    head.appendChild(el("strong", null, "مؤهل"));
    var remove = el("button", null, "حذف");
    remove.type = "button";
    remove.addEventListener("click", function () { entry.remove(); });
    head.appendChild(remove);
    entry.appendChild(head);

    var row1 = el("div", "row");
    row1.appendChild(field("الجامعة/المعهد", "school", data.school));
    row1.appendChild(field("الدرجة", "degree", data.degree));
    entry.appendChild(row1);

    var row2 = el("div", "row");
    row2.appendChild(field("التخصّص", "field_of_study", data.field_of_study));
    row2.appendChild(field("سنة التخرّج", "end_year", data.end_year));
    entry.appendChild(row2);

    educationsHost.appendChild(entry);
  }

  function readEntries(host) {
    return Array.prototype.map.call(host.querySelectorAll(".entry"), function (entry) {
      var data = {};
      entry.querySelectorAll("[data-field]").forEach(function (input) {
        data[input.dataset.field] = input.value.trim();
      });
      return data;
    });
  }

  /* ---------- payload ---------- */

  function buildProfile() {
    var value = function (name) {
      var node = form.elements[name];
      return node ? node.value.trim() : "";
    };
    var number = function (name) {
      var parsed = parseInt(value(name), 10);
      return isNaN(parsed) || parsed < 0 ? 0 : parsed;
    };
    var checked = function (name) {
      var node = form.elements[name];
      return Boolean(node && node.checked);
    };

    return {
      full_name: value("full_name"),
      headline: value("headline"),
      about: value("about"),
      location: value("location"),
      industry: value("industry"),
      target_role: value("target_role"),
      target_keywords: splitList(value("target_keywords")),
      skills: splitList(value("skills")),
      certifications: splitList(value("certifications")),
      languages: splitList(value("languages")),
      experiences: readEntries(experiencesHost),
      educations: readEntries(educationsHost),
      featured_count: number("featured_count"),
      recommendations_count: number("recommendations_count"),
      connections_count: number("connections_count"),
      custom_url: value("custom_url"),
      has_photo: checked("has_photo"),
      has_banner: checked("has_banner"),
    };
  }

  /* ---------- rendering ---------- */

  function meterClass(percent) {
    if (percent < 50) return "meter is-low";
    if (percent < 80) return "meter is-mid";
    return "meter is-high";
  }

  function findingNode(finding) {
    var node = el("div", "finding " + finding.severity);
    var message = el("p", "message");
    var badge = el("span", "badge " + finding.severity, SEVERITY_LABEL[finding.severity] || finding.severity);
    message.appendChild(badge);
    message.appendChild(el("span", "ltr", finding.message));
    node.appendChild(message);
    if (finding.suggestion) {
      node.appendChild(el("p", "suggestion ltr", finding.suggestion));
    }
    return node;
  }

  function render(report) {
    reportPanel.textContent = "";

    var head = el("div", "score-head");
    head.appendChild(el("span", "score-value", report.score.toFixed(1)));
    head.appendChild(el("span", null, "من 100"));
    head.appendChild(el("span", "grade", "التقدير " + report.grade));
    reportPanel.appendChild(head);

    var summary = report.summary;
    reportPanel.appendChild(
      el("p", "hint", summary.critical + " حرجة · " + summary.warning + " تحذيرات · " + summary.info + " ملاحظات")
    );

    var sections = el("div", "sections");
    report.results.forEach(function (result) {
      var row = el("div", "section-row");
      var label = el("div", "section-label");
      label.appendChild(el("span", "ltr", result.title));
      label.appendChild(
        el("span", null, result.applicable ? Math.round(result.score * 100) + "%" : "غير محتسَبة")
      );
      row.appendChild(label);

      var percent = result.applicable ? result.score * 100 : 0;
      var meter = el("div", meterClass(percent));
      var fill = el("div");
      fill.style.width = percent + "%";
      meter.appendChild(fill);
      row.appendChild(meter);
      sections.appendChild(row);
    });
    reportPanel.appendChild(sections);

    if (report.actions.length) {
      reportPanel.appendChild(el("h2", null, "ابدأ بهذه"));
      var list = el("ol", "actions");
      report.actions.forEach(function (action) {
        var item = el("li");
        var message = el("p", "message");
        message.appendChild(el("span", "badge " + action.severity, "+" + action.impact.toFixed(1)));
        message.appendChild(el("span", "ltr", action.message));
        item.appendChild(message);
        if (action.suggestion) item.appendChild(el("p", "suggestion ltr", action.suggestion));
        list.appendChild(item);
      });
      reportPanel.appendChild(list);
    }

    reportPanel.appendChild(el("h2", null, "كل الملاحظات"));
    report.results.forEach(function (result) {
      result.findings.forEach(function (finding) {
        reportPanel.appendChild(findingNode(finding));
      });
    });
  }

  function renderError(message) {
    reportPanel.textContent = "";
    reportPanel.appendChild(el("p", "error", message));
  }

  /* ---------- importing a LinkedIn export ---------- */

  var TEXT_FIELDS = [
    "full_name", "headline", "about", "location", "industry", "custom_url", "target_role",
  ];
  var LIST_FIELDS = ["skills", "certifications", "languages", "target_keywords"];
  var NUMBER_FIELDS = ["connections_count", "recommendations_count", "featured_count"];

  function fillForm(profile) {
    TEXT_FIELDS.forEach(function (name) {
      if (form.elements[name]) form.elements[name].value = profile[name] || "";
    });
    LIST_FIELDS.forEach(function (name) {
      if (form.elements[name]) form.elements[name].value = (profile[name] || []).join(", ");
    });
    NUMBER_FIELDS.forEach(function (name) {
      if (form.elements[name]) form.elements[name].value = profile[name] || 0;
    });
    ["has_photo", "has_banner"].forEach(function (name) {
      if (form.elements[name]) form.elements[name].checked = Boolean(profile[name]);
    });

    experiencesHost.textContent = "";
    educationsHost.textContent = "";
    (profile.experiences || []).forEach(addExperience);
    (profile.educations || []).forEach(addEducation);
    if (!experiencesHost.children.length) addExperience();
    if (!educationsHost.children.length) addEducation();
    updateCounters();
  }

  function importExport(file) {
    var data = new FormData();
    data.append("file", file);
    importStatus.textContent = "جارٍ قراءة " + file.name + " …";
    importStatus.className = "hint";

    fetch("/import", { method: "POST", body: data })
      .then(function (response) {
        return response.json().then(function (payload) {
          if (!response.ok) throw new Error(payload.detail || "الحالة " + response.status);
          return payload;
        });
      })
      .then(function (payload) {
        fillForm(payload.profile);
        importStatus.textContent =
          "تمت قراءة " + payload.files_read.join("، ") + ". راجع الحقول ثم اضغط «حلّل الملف».";
      })
      .catch(function (error) {
        importStatus.textContent = "تعذّر الاستيراد: " + error.message;
        importStatus.className = "error";
      });
  }

  exportInput.addEventListener("change", function () {
    if (exportInput.files && exportInput.files[0]) importExport(exportInput.files[0]);
  });

  /* ---------- wiring ---------- */

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    submitButton.disabled = true;

    fetch("/analyze", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ profile: buildProfile(), max_actions: 5 }),
    })
      .then(function (response) {
        if (!response.ok) throw new Error("الخادم ردّ بالحالة " + response.status);
        return response.json();
      })
      .then(render)
      .catch(function (error) {
        renderError("تعذّر التحليل: " + error.message);
      })
      .finally(function () {
        submitButton.disabled = false;
      });
  });

  document.querySelectorAll("[data-add]").forEach(function (button) {
    button.addEventListener("click", function () {
      if (button.dataset.add === "experience") addExperience();
      else addEducation();
    });
  });

  document.getElementById("load-example").addEventListener("click", function () {
    Object.keys(EXAMPLE).forEach(function (key) {
      var node = form.elements[key];
      if (!node) return;
      if (node.type === "checkbox") node.checked = Boolean(EXAMPLE[key]);
      else node.value = EXAMPLE[key];
    });
    experiencesHost.textContent = "";
    educationsHost.textContent = "";
    EXAMPLE.experiences.forEach(addExperience);
    EXAMPLE.educations.forEach(addEducation);
    updateCounters();
  });

  document.getElementById("reset-form").addEventListener("click", function () {
    form.reset();
    experiencesHost.textContent = "";
    educationsHost.textContent = "";
    addExperience();
    addEducation();
    updateCounters();
    reportPanel.textContent = "";
    reportPanel.appendChild(el("p", "placeholder", "النتيجة ستظهر هنا بعد التحليل."));
  });

  function updateCounters() {
    var headline = form.elements.headline.value;
    var about = form.elements.about.value;
    var words = about.trim() ? about.trim().split(/\s+/).length : 0;
    document.getElementById("headline-count").textContent =
      headline.length + " حرف" + (headline.length > 220 ? " — تجاوزت حد 220" : "");
    document.getElementById("about-count").textContent = about.length + " حرف · " + words + " كلمة";
  }

  form.elements.headline.addEventListener("input", updateCounters);
  form.elements.about.addEventListener("input", updateCounters);

  addExperience();
  addEducation();
  updateCounters();
})();
