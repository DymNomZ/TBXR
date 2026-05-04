from datetime import date

from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .models import Patient


def _parse_date(value: str) -> date | None:
	try:
		return date.fromisoformat(value)
	except ValueError:
		return None


def register_patient(request):
	if request.method != "POST":
		return HttpResponseNotAllowed(["POST"])

	data = request.POST
	errors = {}

	first_name = data.get("first_name", "").strip()
	last_name = data.get("last_name", "").strip()
	date_of_birth_raw = data.get("date_of_birth", "").strip()
	sex = data.get("sex", "").strip().upper()
	contact_number = data.get("contact_number", "").strip()

	if not first_name:
		errors["first_name"] = "First name is required."
	if not last_name:
		errors["last_name"] = "Last name is required."

	if not date_of_birth_raw:
		errors["date_of_birth"] = "Date of birth is required."
		parsed_date_of_birth = None
	else:
		parsed_date_of_birth = _parse_date(date_of_birth_raw)
		if parsed_date_of_birth is None:
			errors["date_of_birth"] = "Use YYYY-MM-DD format."

	valid_sex_values = {choice[0] for choice in Patient.SEX_CHOICES}
	if not sex:
		errors["sex"] = "Sex is required."
	elif sex not in valid_sex_values:
		errors["sex"] = f"Sex must be one of {', '.join(sorted(valid_sex_values))}."

	if errors:
		return JsonResponse({"errors": errors}, status=400)

	patient = Patient.objects.create(
		first_name=first_name,
		last_name=last_name,
		date_of_birth=parsed_date_of_birth,
		sex=sex,
		contact_number=contact_number,
	)

	return redirect(reverse("patients:detail", kwargs={"patient_id": patient.patient_id}))


def patient_detail(request, patient_id):
	patient = get_object_or_404(Patient, patient_id=patient_id)
	return JsonResponse(
		{
			"patient_id": patient.patient_id,
			"first_name": patient.first_name,
			"last_name": patient.last_name,
			"date_of_birth": patient.date_of_birth.isoformat(),
			"sex": patient.sex,
			"contact_number": patient.contact_number,
			"date_created": patient.date_created.isoformat(),
		}
	)
