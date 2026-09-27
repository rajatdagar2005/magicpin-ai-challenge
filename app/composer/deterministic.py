from typing import Dict, Any, Optional


# ============================================================
# HELPERS
# ============================================================

def _first(data: Any, *keys, default=None):
    """Return the first non-empty value for any requested key."""
    if not isinstance(data, (dict, list)):
        return default

    wanted = {str(k).lower() for k in keys}

    def walk(obj):
        if isinstance(obj, dict):
            # Exact matches first.
            for key, value in obj.items():
                if str(key).lower() in wanted:
                    if value is not None and value != "":
                        return value

            # Then nested structures.
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    result = walk(value)
                    if result is not None and result != "":
                        return result

        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    result = walk(item)
                    if result is not None and result != "":
                        return result

        return None

    result = walk(data)
    return result if result is not None and result != "" else default


def _payload(trigger: Dict[str, Any]) -> Dict[str, Any]:
    payload = trigger.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def _merchant_name(merchant: Dict[str, Any]) -> str:
    identity = merchant.get("identity", {})
    if not isinstance(identity, dict):
        return "there"

    return (
        identity.get("owner_first_name")
        or identity.get("name")
        or "there"
    )


def _business_name(merchant: Dict[str, Any]) -> str:
    identity = merchant.get("identity", {})
    if not isinstance(identity, dict):
        return "your business"

    return identity.get("name") or "your business"


def _category_voice(category_slug: str) -> Dict[str, str]:
    voices = {
        "dentists": {
            "greeting": "Dr.",
            "action": "patient",
            "plural": "patients",
        },
        "salons": {
            "greeting": "Hi",
            "action": "client",
            "plural": "clients",
        },
        "restaurants": {
            "greeting": "Hi",
            "action": "guest",
            "plural": "guests",
        },
        "gyms": {
            "greeting": "Hi",
            "action": "member",
            "plural": "members",
        },
        "pharmacies": {
            "greeting": "Hi",
            "action": "customer",
            "plural": "customers",
        },
    }

    return voices.get(
        category_slug,
        {
            "greeting": "Hi",
            "action": "customer",
            "plural": "customers",
        },
    )


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_pct(value) -> str:
    try:
        number = float(value)

        if abs(number) <= 1:
            number *= 100

        return f"{number:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def _safe_pct(value) -> str:
    return _format_pct(value)


def _money(value) -> str:
    if value is None or value == "":
        return ""

    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _offer_text(offer: Optional[Dict[str, Any]]) -> str:
    if not isinstance(offer, dict):
        return ""

    title = offer.get("title")
    if not title:
        return ""

    price = offer.get("price")

    if price is not None:
        return f"{title} at {_money(price)}"

    return str(title)


def _scalar_facts(data: Any) -> Dict[str, Any]:
    """
    Flatten scalar values from nested payloads.

    Used only as a fallback. Internal IDs are excluded.
    """
    facts = {}

    ignored = {
        "id",
        "trigger_id",
        "merchant_id",
        "customer_id",
        "category_id",
        "alert_id",
        "digest_item_id",
        "top_item_id",
        "suppression_key",
    }

    def walk(obj, prefix=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = str(key).lower()

                if key_lower in ignored:
                    continue

                path = f"{prefix}.{key}" if prefix else str(key)

                if isinstance(value, (str, int, float, bool)):
                    facts[key_lower] = value
                    facts[path.lower()] = value

                elif isinstance(value, (dict, list)):
                    walk(value, path)

        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    walk(item, prefix)

    walk(data)
    return facts


def _first_string(values) -> Optional[str]:
    for value in values:
        if value is None:
            continue

        text = str(value).strip()

        if text:
            return text

    return None


def _pretty_token(value) -> str:
    """
    Convert internal-ish tokens into readable text.

    Examples:
        weight_loss -> weight loss
        corporate_bulk_thali_package -> corporate bulk thali package
        post_resolution_window_apr_jun -> post resolution window apr jun
    """
    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    return " ".join(text.split())


def _format_trend(value) -> str:
    """
    Convert:
        ORS_demand_+40 -> ORS demand +40%
        cold_cough_demand_-60 -> cold cough demand -60%
    """
    text = str(value).strip()

    if not text:
        return ""

    parts = text.split("_")

    if len(parts) >= 2:
        last = parts[-1]

        try:
            number = float(last)

            label = " ".join(parts[:-1]).replace("+", "").replace("-", "").strip()

            sign = "+" if number >= 0 else ""

            return f"{_pretty_token(label)} {sign}{number:g}%"
        except ValueError:
            pass

    return _pretty_token(text)


def _join_human(items, conjunction="and"):
    items = [str(x).strip() for x in items if x is not None and str(x).strip()]

    if not items:
        return ""

    if len(items) == 1:
        return items[0]

    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"

    return ", ".join(items[:-1]) + f", {conjunction} {items[-1]}"


def _salutation(category_slug: str, merchant: Dict[str, Any]) -> str:
    voice = _category_voice(category_slug)
    name = _merchant_name(merchant)

    if voice["greeting"] == "Dr.":
        return f"Dr. {name},"

    return f"Hi {name},"


# ============================================================
# MAIN COMPOSER
# ============================================================

def compose(
    category: Dict[str, Any],
    merchant: Dict[str, Any],
    trigger: Dict[str, Any],
    customer: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:

    kind = str(trigger.get("kind", ""))
    scope = str(trigger.get("scope", ""))
    payload = _payload(trigger)

    category_slug = str(category.get("slug", ""))
    voice = _category_voice(category_slug)

    merchant_name = _merchant_name(merchant)
    business_name = _business_name(merchant)

    salutation = _salutation(category_slug, merchant)

    performance = merchant.get("performance", {})
    if not isinstance(performance, dict):
        performance = {}

    subscription = merchant.get("subscription", {})
    if not isinstance(subscription, dict):
        subscription = {}

    active_offers = [
        offer
        for offer in merchant.get("offers", [])
        if isinstance(offer, dict)
        and offer.get("status") == "active"
    ]

    best_offer = active_offers[0] if active_offers else None
    offer_text = _offer_text(best_offer)

    body = ""
    cta = "yes/no"
    rationale = ""
    send_as = "vera"

    # ========================================================
    # CUSTOMER OBJECT PRESENT
    # ========================================================

    if customer is not None:

        send_as = "merchant_on_behalf"

        identity = customer.get("identity", {})
        if not isinstance(identity, dict):
            identity = {}

        customer_name = identity.get("name") or "there"

        language = str(
            identity.get("language_pref", "en")
        ).lower()

        # ----------------------------------------------------
        # RECALL DUE
        # ----------------------------------------------------

        if kind == "recall_due":

            service = _first(
                payload,
                "service_due",
                "service",
                "service_name",
            )

            due_date = _first(
                payload,
                "due_date",
            )

            last_service = _first(
                payload,
                "last_service_date",
            )

            slots = payload.get("available_slots", [])

            slot_labels = []

            if isinstance(slots, list):
                for slot in slots:
                    if isinstance(slot, dict):
                        label = slot.get("label")
                        if label:
                            slot_labels.append(str(label))

            service_text = _pretty_token(service) if service else "follow-up"

            body = (
                f"Hi {customer_name}, this is {business_name}. "
                f"Your {service_text} is due"
            )

            if due_date:
                body += f" on {due_date}"

            if last_service:
                body += f" after your last visit on {last_service}"

            body += "."

            if len(slot_labels) >= 2:
                body += (
                    f" We have {slot_labels[0]} or "
                    f"{slot_labels[1]} available."
                )
                body += (
                    " Reply 1 or 2 to pick a slot, "
                    "or send us another preferred time."
                )
            elif len(slot_labels) == 1:
                body += (
                    f" We have {slot_labels[0]} available. "
                    "Reply if you'd like to book it."
                )
            else:
                body += (
                    " Reply with your preferred time "
                    "and we'll help schedule it."
                )

            cta = "choose_time"

            rationale = (
                "Customer recall grounded in service, due date, "
                "previous service date, and available slots."
            )

        # ----------------------------------------------------
        # SOFT LAPSED
        # ----------------------------------------------------

        elif kind == "customer_lapsed_soft":

            days = _first(
                payload,
                "days_lapsed",
                "days_since_last_visit",
            )

            months = _first(
                payload,
                "months_lapsed",
                "months_since_last_visit",
            )

            focus = _first(
                payload,
                "previous_focus",
                "service",
                "service_name",
            )

            body = f"Hi {customer_name}, this is {business_name}. "

            if days is not None:
                body += (
                    f"We haven't seen you for {days} days"
                )
            elif months is not None:
                body += (
                    f"We haven't seen you for {months} months"
                )
            else:
                body += "It's been a while since your last visit"

            if focus:
                body += (
                    f", and your previous focus was "
                    f"{_pretty_token(focus)}"
                )

            body += (
                ". Want to pick up where you left off?"
            )

            cta = "yes/no"

            rationale = (
                "Lapsed customer outreach grounded in available "
                "recency and service-interest facts."
            )

        # ----------------------------------------------------
        # APPOINTMENT TOMORROW
        # ----------------------------------------------------

        elif kind == "appointment_tomorrow":

            appointment_time = _first(
                payload,
                "appointment_time",
                "slot",
                "time",
            )

            body = (
                f"Hi {customer_name}, this is a reminder from "
                f"{business_name} for your appointment tomorrow"
            )

            if appointment_time:
                body += f" at {appointment_time}"

            body += (
                ". Reply YES to confirm or RESCHEDULE "
                "if you need another time."
            )

            cta = "confirm/cancel"

            rationale = "Appointment reminder with clear confirmation CTA."

        # ----------------------------------------------------
        # OTHER CUSTOMER TRIGGERS
        # ----------------------------------------------------

        elif kind == "wedding_package_followup":

            wedding_date = _first(
                payload,
                "wedding_date",
            )

            days = _first(
                payload,
                "days_to_wedding",
            )

            next_step = _first(
                payload,
                "next_step_window_open",
            )

            body = (
                f"Hi {customer_name}, this is {business_name}. "
                "Your bridal planning is coming up"
            )

            if wedding_date:
                body += f" for {wedding_date}"

            if days is not None:
                body += f" ({days} days away)"

            if next_step:
                body += (
                    f". The next step is "
                    f"{_pretty_token(next_step)}"
                )

            body += (
                ". Reply YES if you'd like us to help "
                "plan the next step."
            )

            cta = "yes/no"

            rationale = (
                "Bridal follow-up grounded in wedding timing "
                "and next-step window."
            )

        elif kind == "customer_lapsed_hard":

            days = _first(
                payload,
                "days_since_last_visit",
                "days_lapsed",
            )

            focus = _first(
                payload,
                "previous_focus",
            )

            membership_months = _first(
                payload,
                "previous_membership_months",
            )

            body = f"Hi {customer_name}, this is {business_name}. "

            if days is not None:
                body += f"We haven't seen you for {days} days"
            else:
                body += "It's been a while since your last visit"

            if focus:
                body += (
                    f", and your previous focus was "
                    f"{_pretty_token(focus)}"
                )

            if membership_months is not None:
                body += (
                    f" after a {membership_months}-month membership"
                )

            body += (
                ". Want me to help you get started again?"
            )

            cta = "yes/no"

            rationale = (
                "Hard-lapsed customer outreach grounded in "
                "visit recency, previous focus, and membership history."
            )

        elif kind == "trial_followup":

            trial_date = _first(
                payload,
                "trial_date",
            )

            options = payload.get("next_session_options", [])

            option_labels = []

            if isinstance(options, list):
                for option in options:
                    if isinstance(option, dict) and option.get("label"):
                        option_labels.append(str(option["label"]))

            body = (
                f"Hi {customer_name}, this is {business_name}. "
            )

            if trial_date:
                body += f"Your trial was on {trial_date}"
            else:
                body += "You recently completed your trial"

            if option_labels:
                body += (
                    f". The next available session is "
                    f"{option_labels[0]}"
                )

            body += (
                ". Reply YES if you'd like to continue."
            )

            cta = "yes/no"

            rationale = (
                "Trial follow-up grounded in trial date "
                "and available next session."
            )

        elif kind == "chronic_refill_due":

            medicines = payload.get("molecule_list", [])

            if isinstance(medicines, list):
                medicine_text = _join_human(
                    [_pretty_token(x) for x in medicines]
                )
            else:
                medicine_text = _pretty_token(medicines)

            runout = _first(
                payload,
                "stock_runs_out_iso",
            )

            body = (
                f"Hi {customer_name}, this is {business_name}. "
            )

            if medicine_text:
                body += (
                    f"Your refill includes {medicine_text}"
                )
            else:
                body += "Your chronic medication refill is due"

            if runout:
                body += f", with supply running out around {runout}"

            body += (
                ". Reply YES if you'd like us to help arrange it."
            )

            cta = "yes/no"

            rationale = (
                "Chronic refill outreach grounded in medication "
                "list and projected stock-out timing."
            )

        else:

            # Customer-safe generic fallback.
            fact = _first(
                payload,
                "message",
                "summary",
                "description",
                "service",
                "service_name",
                "event",
                "event_name",
                "title",
            )

            body = (
                f"Hi {customer_name}, this is {business_name}."
            )

            if fact:
                body += f" {_pretty_token(fact)}."

            body += " Reply YES and we'll share the details."

            cta = "yes/no"

            rationale = (
                "Customer message grounded in available payload context."
            )

        return {
            "body": body,
            "cta": cta,
            "send_as": send_as,
            "rationale": rationale,
        }

    # ========================================================
    # MERCHANT-SIDE TRIGGERS
    # ========================================================

    # --------------------------------------------------------
    # RESEARCH DIGEST
    # --------------------------------------------------------

    if kind == "research_digest":

        digest_id = payload.get("top_item_id")

        digest = category.get("digest", [])

        item = None

        if isinstance(digest, list):
            item = next(
                (
                    x for x in digest
                    if isinstance(x, dict)
                    and x.get("id") == digest_id
                ),
                None,
            )

        if item:
            title = item.get(
                "title",
                "A new research update",
            )

            source = item.get("source")

            body = f"{salutation} {title}"

            if source:
                body += f" — {source}"

            body += (
                ". Want me to summarize the key takeaway "
                "and turn it into one practical action?"
            )

        else:
            body = (
                f"{salutation} there's a new research update "
                "relevant to your practice. Want me to summarize it?"
            )

        cta = "yes/no"
        rationale = "Research update grounded in available digest metadata."

    # --------------------------------------------------------
    # REGULATION CHANGE
    # --------------------------------------------------------

    elif kind == "regulation_change":

        deadline = _first(
            payload,
            "deadline_iso",
            "deadline",
        )

        item_id = _first(
            payload,
            "top_item_id",
            "digest_item_id",
        )

        body = (
            f"{salutation} there's a regulatory update "
            "relevant to your practice"
        )

        if deadline:
            body += f", with a deadline of {deadline}"

        if item_id:
            body += "."

        else:
            body += "."

        body += (
            " Want me to summarize the requirement "
            "and turn it into a practical checklist?"
        )

        cta = "yes/no"

        rationale = (
            "Regulatory trigger grounded in deadline and "
            "available source item metadata."
        )

    # --------------------------------------------------------
    # PERFORMANCE DIP
    # --------------------------------------------------------

    elif kind == "perf_dip":

        metric = _first(
            payload,
            "metric",
        )

        delta = _first(
            payload,
            "delta_pct",
            "change_pct",
        )

        window = _first(
            payload,
            "window",
        )

        baseline = _first(
            payload,
            "vs_baseline",
        )

        metric_text = _pretty_token(metric) if metric else "performance"

        body = f"{salutation} "

        if delta is not None:
            direction = "down" if (_safe_float(delta) or 0) < 0 else "up"
            body += (
                f"{metric_text} are {direction} "
                f"{_safe_pct(abs(_safe_float(delta) or 0))}"
            )
        else:
            body += f"{metric_text} have softened"

        if window:
            body += f" over the last {window}"

        if baseline is not None:
            body += f", versus a baseline of {baseline}"

        body += (
            ". Want me to check the profile and suggest "
            "one conversion-focused change?"
        )

        cta = "yes/no"

        rationale = (
            "Performance decline tied directly to metric, "
            "change, window, and baseline facts."
        )

    # --------------------------------------------------------
    # SEASONAL PERFORMANCE DIP
    # --------------------------------------------------------

    elif kind == "seasonal_perf_dip":

        metric = _first(payload, "metric")
        delta = _first(payload, "delta_pct")
        window = _first(payload, "window")
        note = _first(payload, "season_note")
        expected = _first(payload, "is_expected_seasonal")

        metric_text = _pretty_token(metric) if metric else "performance"

        body = f"{salutation} "

        if delta is not None:
            body += (
                f"{metric_text} are down "
                f"{_safe_pct(abs(_safe_float(delta) or 0))}"
            )
        else:
            body += f"{metric_text} have softened"

        if window:
            body += f" over {window}"

        if expected is True:
            body += " and this is flagged as an expected seasonal dip"

        if note:
            body += f" ({_pretty_token(note)})"

        body += (
            ". Want me to suggest a low-effort seasonal adjustment "
            "rather than overreacting to the dip?"
        )

        cta = "yes/no"

        rationale = (
            "Seasonal performance decline distinguished from "
            "a generic performance problem using supplied context."
        )

    # --------------------------------------------------------
    # PERFORMANCE SPIKE
    # --------------------------------------------------------

    elif kind == "perf_spike":

        metric = _first(payload, "metric")
        delta = _first(payload, "delta_pct")
        window = _first(payload, "window")
        baseline = _first(payload, "vs_baseline")
        driver = _first(payload, "likely_driver")

        metric_text = _pretty_token(metric) if metric else "performance"

        body = f"{salutation} "

        if delta is not None:
            body += (
                f"{metric_text} are up "
                f"{_safe_pct(delta)}"
            )
        else:
            body += f"{metric_text} are trending up"

        if window:
            body += f" over {window}"

        if baseline is not None:
            body += f", with a baseline of {baseline}"

        if driver:
            body += (
                f". The likely driver is "
                f"{_pretty_token(driver)}"
            )

        body += (
            ". Want me to turn what's working into "
            "one repeatable promotion?"
        )

        cta = "yes/no"

        rationale = (
            "Performance improvement grounded in metric, "
            "magnitude, baseline, and likely driver."
        )

    # --------------------------------------------------------
    # REVIEW THEME
    # --------------------------------------------------------

    elif kind == "review_theme_emerged":

        theme = _first(
            payload,
            "theme",
            "review_theme",
        )

        occurrences = _first(
            payload,
            "occurrences_30d",
            "review_count",
        )

        trend = _first(
            payload,
            "trend",
        )

        quote = _first(
            payload,
            "common_quote",
        )

        body = f"{salutation} "

        if occurrences is not None:
            body += f"{occurrences} reviews in the last 30 days"
        else:
            body += "recent reviews"

        if theme:
            body += f" are highlighting {_pretty_token(theme)}"

        if trend:
            body += f", and the trend is {trend}"

        if quote:
            body += f". One common comment was: “{quote}”"

        body += (
            ". Want me to draft a response and one operational fix?"
        )

        cta = "approve draft"

        rationale = (
            "Review signal grounded in theme, frequency, trend, "
            "and supplied customer language."
        )

    # --------------------------------------------------------
    # COMPETITOR
    # --------------------------------------------------------

    elif kind == "competitor_opened":

        name = _first(payload, "competitor_name")
        distance = _first(payload, "distance_km")
        offer = _first(payload, "their_offer")
        opened = _first(payload, "opened_date")

        body = f"{salutation} "

        if name:
            body += f"{name} opened nearby"
        else:
            body += "a new competitor opened nearby"

        if distance is not None:
            body += f", {float(distance):.1f} km away"

        if opened:
            body += f" on {opened}"

        if offer:
            body += f", offering {offer}"

        body += "."

        if offer_text:
            body += f" You already have {offer_text}."

        body += (
            " Want me to draft a retention message "
            "for existing customers?"
        )

        cta = "yes/no"

        rationale = (
            "Competitor threat grounded in name, distance, "
            "date, and competitor offer."
        )

    # --------------------------------------------------------
    # CTR COMPARISON
    # --------------------------------------------------------

    elif kind == "ctr_comparison":

        ctr = _first(
            payload,
            "ctr",
            "current_ctr",
            default=performance.get("ctr"),
        )

        peer_ctr = _first(
            payload,
            "peer_ctr",
            "benchmark_ctr",
            "avg_ctr",
            default=category.get("peer_stats", {}).get("avg_ctr")
            if isinstance(category.get("peer_stats", {}), dict)
            else None,
        )

        scope = _first(
            payload,
            "peer_scope",
            "benchmark_scope",
            default=(
                category.get("peer_stats", {}).get("scope", "peers")
                if isinstance(category.get("peer_stats", {}), dict)
                else "peers"
            ),
        )

        body = f"{salutation} "

        if ctr is not None and peer_ctr is not None:
            body += (
                f"your CTR is {_safe_pct(ctr)} vs "
                f"{_safe_pct(peer_ctr)} across {scope}"
            )
        elif ctr is not None:
            body += f"your CTR is {_safe_pct(ctr)}"
        else:
            body += "your profile conversion data needs a closer look"

        body += (
            ". Want me to suggest one profile or offer change "
            "to improve conversion?"
        )

        cta = "yes/no"

        rationale = (
            "CTR comparison grounded in merchant and peer metrics."
        )

    # --------------------------------------------------------
    # DORMANT
    # --------------------------------------------------------

    elif kind == "dormant_with_vera":

        days = _first(
            payload,
            "days_since_last_merchant_message",
        )

        topic = _first(
            payload,
            "last_topic",
        )

        body = f"{salutation} "

        if days is not None:
            body += (
                f"it's been {days} days since your last merchant "
                "conversation"
            )
        else:
            body += "your merchant conversation has gone quiet"

        if topic:
            body += f", with the last topic being {_pretty_token(topic)}"

        body += (
            ". Want me to restart the conversation with "
            "a useful next step?"
        )

        cta = "yes/no"

        rationale = (
            "Dormancy signal grounded in conversation recency "
            "and last topic."
        )

    # --------------------------------------------------------
    # MERCHANT RECALL
    # --------------------------------------------------------

    elif kind == "recall_due":

        count = _first(
            payload,
            "due_count",
            "patients_due",
            "customer_count",
        )

        body = f"{salutation} "

        if count is not None:
            body += (
                f"{count} {voice['plural']} are due for recall"
            )
        else:
            body += f"you have {voice['plural']} due for recall"

        if offer_text:
            body += f". You could pair the reminder with {offer_text}"

        body += ". Want me to draft the reminder?"

        cta = "yes/no"

        rationale = (
            "Recall outreach grounded in due count and active offer."
        )

    # --------------------------------------------------------
    # FESTIVAL
    # --------------------------------------------------------

    elif kind == "festival_upcoming":

        festival = _first(
            payload,
            "festival",
            "event_name",
        )

        date = _first(
            payload,
            "date",
        )

        days = _first(
            payload,
            "days_until",
        )

        relevant = payload.get("category_relevance", [])

        body = f"{salutation} "

        if festival:
            body += f"{festival} is coming up"
        else:
            body += "a seasonal event is coming up"

        if date:
            body += f" on {date}"

        if days is not None:
            body += f" ({days} days away)"

        if isinstance(relevant, list) and relevant:
            readable = _join_human(
                [_pretty_token(x) for x in relevant]
            )
            body += f". Relevant categories include {readable}"

        body += "."

        if offer_text:
            body += f" You already have {offer_text}."

        body += " Want me to draft a seasonal campaign?"

        cta = "yes/no"

        rationale = (
            "Festival opportunity grounded in date, timing, "
            "category relevance, and offer context."
        )

    # --------------------------------------------------------
    # RENEWAL
    # --------------------------------------------------------

    elif kind == "renewal_due":

        days = _first(
            payload,
            "days_remaining",
            "days_to_expiry",
            default=subscription.get("days_remaining"),
        )

        plan = _first(
            payload,
            "plan",
            default=subscription.get("plan"),
        )

        amount = _first(
            payload,
            "renewal_amount",
        )

        body = f"{salutation} "

        if plan:
            body += f"your {plan} plan"
        else:
            body += "your plan"

        if days is not None:
            body += f" expires in {days} days"

        if amount is not None:
            body += f" and renewal is {_money(amount)}"

        body += (
            ". Want me to share the renewal link?"
        )

        cta = "yes/no"

        rationale = (
            "Renewal reminder grounded in plan, timing, and amount."
        )

    # --------------------------------------------------------
    # MILESTONE
    # --------------------------------------------------------

    elif kind == "milestone_reached":

        metric = _first(
            payload,
            "metric",
        )

        current = _first(
            payload,
            "value_now",
            "current_value",
        )

        milestone = _first(
            payload,
            "milestone_value",
        )

        imminent = _first(
            payload,
            "is_imminent",
        )

        metric_text = _pretty_token(metric) if metric else "metric"

        body = f"{salutation} "

        if current is not None and milestone is not None:
            body += (
                f"you're at {current} {metric_text}, "
                f"with the {milestone} milestone"
            )
        elif current is not None:
            body += (
                f"you're at {current} {metric_text}"
            )
        elif milestone is not None:
            body += (
                f"the {milestone} {metric_text} milestone "
                "is in sight"
            )
        else:
            body += "you've reached a new milestone"

        if imminent:
            body += " and it's close"

        body += (
            ". Want me to draft a short message "
            "to capitalize on the milestone?"
        )

        cta = "yes/no"

        rationale = (
            "Milestone message grounded in metric, current value, "
            "target milestone, and imminence."
        )

    # ========================================================
    # SALON
    # ========================================================

    elif kind == "wedding_package_followup":

        wedding_date = _first(
            payload,
            "wedding_date",
        )

        days = _first(
            payload,
            "days_to_wedding",
        )

        next_step = _first(
            payload,
            "next_step_window_open",
        )

        trial = _first(
            payload,
            "trial_completed",
        )

        body = f"{salutation} "

        if wedding_date:
            body += f"the bridal booking is tied to {wedding_date}"

        else:
            body += "there's an active bridal follow-up"

        if days is not None:
            body += f", {days} days away"

        if trial:
            body += f", with the trial completed on {trial}"

        if next_step:
            body += (
                f". The next step is "
                f"{_pretty_token(next_step)}"
            )

        body += (
            ". Want me to draft a follow-up asking "
            "for confirmation?"
        )

        cta = "approve draft"

        rationale = (
            "Bridal follow-up grounded in wedding date, "
            "trial date, and next-step program."
        )

    elif kind == "curious_ask_due":

        ask = _first(
            payload,
            "ask_template",
        )

        last_ask = _first(
            payload,
            "last_ask_at",
        )

        body = f"{salutation} "

        if ask:
            body += (
                f"your next useful customer question to explore is "
                f"“{_pretty_token(ask)}”"
            )
        else:
            body += "there's a customer-interest question worth exploring"

        if last_ask:
            body += f"; the last ask was {last_ask}"

        body += ". Want me to turn it into a quick customer prompt?"

        cta = "approve draft"

        rationale = (
            "Curiosity prompt grounded in the supplied ask template "
            "and previous ask timing."
        )

    elif kind == "winback_eligible":

        days = _first(
            payload,
            "days_since_expiry",
            "days_lapsed",
        )

        dip = _first(
            payload,
            "perf_dip_pct",
        )

        added = _first(
            payload,
            "lapsed_customers_added_since_expiry",
        )

        body = f"{salutation} "

        if days is not None:
            body += (
                f"you have customers lapsed for about {days} days"
            )
        else:
            body += "you have a win-back opportunity"

        if added is not None:
            body += (
                f", with {added} added since expiry"
            )

        if dip is not None:
            body += (
                f"; performance is down {_safe_pct(abs(_safe_float(dip) or 0))}"
            )

        body += (
            ". Want me to draft a targeted win-back message?"
        )

        cta = "approve draft"

        rationale = (
            "Win-back signal grounded in inactivity, "
            "customer accumulation, and performance change."
        )

    # ========================================================
    # RESTAURANTS
    # ========================================================

    elif kind == "ipl_match_today":

        match = _first(
            payload,
            "match",
            "match_name",
            "event_name",
        )

        venue = _first(
            payload,
            "venue",
        )

        city = _first(
            payload,
            "city",
        )

        time = _first(
            payload,
            "match_time_iso",
            "match_time",
            "start_time",
        )

        weeknight = _first(
            payload,
            "is_weeknight",
        )

        body = f"{salutation} "

        if match:
            body += f"{match} is on today"
        else:
            body += "there's a match today"

        if venue:
            body += f" at {venue}"

        if city:
            body += f" in {city}"

        if time:
            body += f", starting at {time}"

        if weeknight is False:
            body += ", so it's a strong match-day planning window"

        body += "."

        if offer_text:
            body += f" You already have {offer_text}."

        body += (
            " Want me to draft a match-day message "
            "for nearby customers?"
        )

        cta = "approve draft"

        rationale = (
            "Match-day restaurant opportunity grounded in "
            "match, venue, city, timing, and offer data."
        )

    elif kind == "review_theme_emerged":
        # Kept above intentionally.
        pass

    elif kind == "active_planning_intent":

        topic = _first(
            payload,
            "intent_topic",
        )

        last_message = _first(
            payload,
            "merchant_last_message",
        )

        topic_text = _pretty_token(topic) if topic else "the planned event"

        body = (
            f"{salutation} you're actively planning "
            f"{topic_text}"
        )

        if last_message:
            body += (
                f'. Your latest message was “{last_message}”'
            )

        body += (
            ". Want me to turn this into a concrete "
            "package outline with pricing and next steps?"
        )

        cta = "approve draft"

        rationale = (
            "Planning intent grounded in the exact topic "
            "and merchant's latest message."
        )

    # ========================================================
    # GYMS
    # ========================================================

    elif kind == "customer_lapsed_hard":

        days = _first(
            payload,
            "days_since_last_visit",
        )

        focus = _first(
            payload,
            "previous_focus",
        )

        membership_months = _first(
            payload,
            "previous_membership_months",
        )

        body = f"{salutation} "

        if days is not None:
            body += f"a member hasn't visited for {days} days"
        else:
            body += "a member has lapsed"

        if focus:
            body += (
                f", with previous focus on "
                f"{_pretty_token(focus)}"
            )

        if membership_months is not None:
            body += (
                f" after a {membership_months}-month membership"
            )

        body += (
            ". Want me to draft a personalized win-back message?"
        )

        cta = "approve draft"

        rationale = (
            "Hard-lapse signal grounded in inactivity, "
            "previous fitness goal, and membership history."
        )

    elif kind == "trial_followup":

        trial_date = _first(
            payload,
            "trial_date",
        )

        options = payload.get("next_session_options", [])

        labels = []

        if isinstance(options, list):
            for option in options:
                if isinstance(option, dict):
                    label = option.get("label")
                    if label:
                        labels.append(str(label))

        body = f"{salutation} "

        if trial_date:
            body += f"trial activity was recorded on {trial_date}"
        else:
            body += "trial members need a follow-up"

        if labels:
            body += (
                f"; the next available session is {labels[0]}"
            )

        body += (
            ". Want me to draft a short conversion follow-up?"
        )

        cta = "approve draft"

        rationale = (
            "Trial follow-up grounded in trial timing "
            "and actual next-session availability."
        )

    # ========================================================
    # PHARMACY
    # ========================================================

    elif kind == "supply_alert":

        molecule = _first(
            payload,
            "molecule",
        )

        batches = payload.get("affected_batches", [])

        manufacturer = _first(
            payload,
            "manufacturer",
        )

        body = f"{salutation} "

        if molecule:
            body += f"{molecule} has a supply alert"
        else:
            body += "a medicine has a supply alert"

        if manufacturer:
            body += f" from {manufacturer}"

        if isinstance(batches, list) and batches:
            batch_text = _join_human(
                [str(x) for x in batches]
            )
            body += f"; affected batches are {batch_text}"

        body += (
            ". Want me to prepare the affected-batch "
            "checklist for your inventory?"
        )

        cta = "yes/no"

        rationale = (
            "Supply alert grounded in medicine, manufacturer, "
            "and affected batch information."
        )

    elif kind == "chronic_refill_due":

        medicines = payload.get("molecule_list", [])

        last_refill = _first(
            payload,
            "last_refill",
        )

        runout = _first(
            payload,
            "stock_runs_out_iso",
        )

        address_saved = _first(
            payload,
            "delivery_address_saved",
        )

        if isinstance(medicines, list):
            medicine_text = _join_human(
                [_pretty_token(x) for x in medicines]
            )
        else:
            medicine_text = _pretty_token(medicines)

        body = f"{salutation} "

        if medicine_text:
            body += (
                f"the chronic-refill list includes "
                f"{medicine_text}"
            )
        else:
            body += "customers are due for chronic medication refills"

        if last_refill:
            body += f"; last refill was {last_refill}"

        if runout:
            body += f"; projected stock-out is {runout}"

        if address_saved:
            body += "; the delivery address is already saved"

        body += (
            ". Want me to prepare the refill outreach?"
        )

        cta = "approve draft"

        rationale = (
            "Chronic refill action grounded in actual medicine list, "
            "refill timing, stock-out date, and delivery status."
        )

    elif kind == "category_seasonal":

        season = _first(
            payload,
            "season",
        )

        trends = payload.get("trends", [])

        shelf_action = _first(
            payload,
            "shelf_action_recommended",
        )

        trend_texts = []

        if isinstance(trends, list):
            for trend in trends:
                formatted = _format_trend(trend)
                if formatted:
                    trend_texts.append(formatted)

        body = f"{salutation} "

        if season:
            body += (
                f"{_pretty_token(season)} demand is shifting"
            )
        else:
            body += "seasonal demand is shifting"

        if trend_texts:
            body += (
                f": {_join_human(trend_texts)}"
            )

        if shelf_action:
            body += (
                ". A shelf-priority change is recommended"
            )

        body += (
            ". Want me to turn these trends into "
            "a focused shelf plan?"
        )

        cta = "approve draft"

        rationale = (
            "Seasonal pharmacy signal grounded in explicit "
            "product-level demand changes and shelf recommendation."
        )

    # ========================================================
    # GOOGLE BUSINESS PROFILE
    # ========================================================

    elif kind == "gbp_unverified":

        verified = _first(
            payload,
            "verified",
        )

        path = _first(
            payload,
            "verification_path",
        )

        uplift = _first(
            payload,
            "estimated_uplift_pct",
        )

        body = f"{salutation} "

        if verified is False:
            body += "your Google Business Profile is not verified"
        else:
            body += "your Google Business Profile needs verification"

        if path:
            body += (
                f"; available verification route: "
                f"{_pretty_token(path)}"
            )

        if uplift is not None:
            body += (
                f". The supplied estimate is "
                f"{_safe_pct(uplift)} potential uplift"
            )

        body += (
            ". Want me to walk through the verification step?"
        )

        cta = "yes/no"

        rationale = (
            "GBP issue grounded in verification status, "
            "available verification route, and supplied uplift estimate."
        )

    # ========================================================
    # CDE
    # ========================================================

    elif kind == "cde_opportunity":

        item_id = _first(
            payload,
            "digest_item_id",
        )

        credits = _first(
            payload,
            "credits",
        )

        fee = _first(
            payload,
            "fee",
        )

        body = (
            f"{salutation} there's a professional-learning "
            "opportunity relevant to your practice"
        )

        if credits is not None:
            body += f" with {credits} credits"

        if fee:
            body += f"; access is {str(fee).replace('_', ' ')}"

        if item_id:
            body += f" (reference {item_id})"

        body += (
            ". Want me to summarize the opportunity "
            "and key details?"
        )

        cta = "yes/no"

        rationale = (
            "CDE opportunity grounded in credits, fee status, "
            "and supplied digest reference."
        )

    # ========================================================
    # FINAL GENERIC FALLBACK
    # ========================================================

    else:

        facts = _scalar_facts(payload)

        fact = _first(
            payload,
            "message",
            "summary",
            "description",
            "insight",
            "headline",
            "event_name",
            "event",
            "title",
            "opportunity",
            "service",
            "service_name",
            "theme",
            "category",
            "product",
            "product_name",
            "medicine",
            "medicine_name",
        )

        if not fact:
            candidates = []

            for key, value in facts.items():

                if not isinstance(value, str):
                    continue

                text = value.strip()

                if len(text) < 4:
                    continue

                key_lower = key.lower()

                if any(
                    token in key_lower
                    for token in (
                        "id",
                        "uuid",
                        "url",
                        "date",
                        "time",
                        "timestamp",
                    )
                ):
                    continue

                candidates.append(text)

            if candidates:
                fact = max(candidates, key=len)

        if fact:
            body = (
                f"{salutation} {_pretty_token(fact)}. "
                "Want me to suggest the next step?"
            )
        else:
            body = (
                f"{salutation} I have a new business signal "
                "for your profile. Want me to review it?"
            )

        cta = "yes/no"

        rationale = (
            "Fallback grounded in the most relevant human-readable "
            "fact available in the supplied trigger payload."
        )

    return {
        "body": body,
        "cta": cta,
        "send_as": send_as,
        "rationale": rationale,
    }