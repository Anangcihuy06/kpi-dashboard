# Jira Integration Setup Guide

## 📋 Prerequisites

Sebelum setup Jira integration, pastikan Anda memiliki:
- **Jira Account** dengan akses ke board yang akan di-sync
- **Jira API Token** - Bisa dibuat di: https://id.atlassian.com/manage-profile/security/api-tokens
- **Jira Board ID** - Board ID dari Jira yang berisi sprints
- **Jira URL** - URL instance Jira Anda (contoh: `https://yourcompany.atlassian.net`)
- **Story Points Field ID** - Custom field ID untuk Story Points (default: `customfield_10016`)

## 🚀 Setup Instructions

### 1. Buat Jira API Token

1. Login ke Jira
2. Pergi ke: https://id.atlassian.com/manage-profile/security/api-tokens
3. Click **Create API token**
4. Label token (contoh: "KPI Dashboard")
5. Copy token yang di-generate (hanya muncul sekali!)

### 2. Dapatkan Jira Board ID

1. Buka Jira Board yang ingin di-sync
2. Lihat URL - board ID ada di URL:
   - Contoh: `https://yourcompany.atlassian.net/jira/software/c/projects/PROJ/boards/123`
   - Board ID: `123`

### 3. Cek Story Points Field ID

1. Buka issue apapun di Jira
2. Klik gear icon > View Field Settings
3. Cari "Story Points" field
4. Copy field ID (biasanya `customfield_10016`)

### 4. Configure di KPI Dashboard

1. Buka KPI Dashboard: `http://localhost:5173`
2. Login sebagai user dengan role `ROLE_ADMIN`
3. Pergi ke **Configurator** (atau Admin Panel)
4. Isi **Jira Integration Settings**:

```
Jira URL: https://yourcompany.atlassian.net
Jira Email: your-email@company.com
Jira Token: [paste API token dari step 1]
Board ID: [paste board ID dari step 2]
Story Points Field: customfield_10016 (default)
```

5. Click **Save Integration Settings**

### 5. Test Sync

#### Manual Sync:
1. Setelah konfigurasi selesai, sistem akan auto-sync setiap 60 menit
2. Untuk manual sync, sistem akan memicu job di background:
   - POST `http://localhost:8000/api/v1/sync/trigger`
   - Cek status di: `http://localhost:8000/api/v1/sync/status`

#### Cek Logs:
- Buka terminal backend untuk melihat sync logs:
  ```
  INFO:Scheduler:Starting active sprints sync from Jira...
  INFO:Scheduler:Found 2 active sprint(s) in Jira
  INFO:Scheduler:Creating new active sprint: Sprint 1 (ID: 100)
  INFO:Scheduler:Active sprint sync completed. Total: 2 sprint(s)
  ```

### 6. Verifikasi Data

1. Cek sprint data:
   ```bash
   curl http://localhost:8000/api/v1/sprints
   ```

2. Pastikan `jira_sprint_id` tidak null:
   ```json
   [
     {
       "id": "uuid",
       "sprint_name": "Sprint 1",
       "jira_sprint_id": "100",  <-- Harus terisi
       "status": "ACTIVE",
       "start_date": "2026-08-01T...",
       "end_date": "2026-08-15T..."
     }
   ]
   ```

## 🔧 Troubleshooting

### Issue: "Jira settings incomplete" 
**Solusi**: Pastikan semua field di integration settings terisi (URL, email, token, board ID)

### Issue: "Failed to fetch Jira sprints: 401"
**Solusi**: 
- Cek API token (bisa saja expired)
- Pastikan email dan token benar
- Verifikasi token permission

### Issue: "Failed to fetch Jira sprints: 404"
**Solusi**:
- Cek Jira URL format (pastikan tidak ada trailing `/`)
- Verifikasi Board ID ada benar dan user punya akses

### Issue: "Failed to fetch Jira sprints: 403"
**Solusi**:
- User tidak punya permission ke board
- Token tidak punya permission yang cukup

### Issue: Sprint sync tapi tidak ada data
**Solusi**:
- Cek apakah board tersebut memiliki active/closed sprints
- Pastikan Jira board menggunakan Agile/Scrum method
- Cek filter sprint di Jira

### Issue: Scheduler tidak jalan
**Solusi**:
- Pastikan scheduler sudah start: `INFO:Scheduler:Scheduler started successfully`
- Cek environment variables: `SYNC_SPRINTS_INTERVAL_MINUTES=60`
- Restart backend server

## 📱 Jira Token Security

⚠️ **IMPORTANT**:
- API token hanya muncul sekali saat dibuat
- Jangan share token ke orang lain
- Token disimpan terenkripsi di database
- Jika token bocor, revoke dan buat baru

## 🔄 Sync Frequency

Default configuration:
- **Sprint Sync**: Setiap 60 menit
- **KPI Calculation**: Setiap 60 menit

Customizable via environment variables:
```bash
# backend/.env
SYNC_SPRINTS_INTERVAL_MINUTES=30
SYNC_KPI_CALCULATION_INTERVAL_MINUTES=30
```

## ✅ Verification Checklist

- [ ] Jira API token dibuat dan disimpan
- [ ] Jira Board ID tercatat
- [ ] Story Points field ID diketahui
- [ ] Integration settings diisi di dashboard
- [ ] Scheduler logs menunjukkan sync berhasil
- [ ] Sprint data muncul dengan `jira_sprint_id` terisi
- [ ] No error logs di backend terminal

## 🎯 Next Steps

Setelah sprint sync berhasil:
1. Konfigurasi GitLab integration (opsional)
2. Setup user mapping (user_id ke jira_account_id)
3. Test KPI calculation untuk active sprint
4. Setup team hierarchy jika perlu

---

**Contact IT Support** jika mengalami issues yang tidak terdokumentasi di sini.