#!/bin/bash

echo "🔧 Correction de tous les fichiers admin.py..."

cd /home/samnick-humanity/plateforme_municipale/backend

for app in accounts activites annuaires archives dechets etat_civil paiements signature_electronique; do
if [ -f "$app/admin.py" ]; then
echo "📝 Correction de $app/admin.py"

cat > "$app/admin.py" << 'ADMINEOF'
from django.contrib import admin
from .models import *

for model in [model for model in globals().values() if hasattr(model, '_meta') and model._meta.app_label == 'APP_NAME']:
try:
admin.site.register(model)
except:
pass
ADMINEOF

sed -i "s/APP_NAME/$app/g" "$app/admin.py"
fi
done

echo "✅ Tous les fichiers admin.py ont été corrigés"
