# Supabase Storage Integration - Setup Guide

## Overview

This document explains how to configure Supabase Storage for file uploads in the Loopin Backend. The system uses Supabase Storage buckets for user profile pictures and event cover images.

## Prerequisites

1. **Supabase Account** with an active project
2. **Two Storage Buckets Created**:
   - `user-profiles` (public bucket)
   - `event-images` (public bucket)

---

## Step 1: Supabase Project Configuration

### Required Environment Variables

Add these to your `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**Where to find these values:**
1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **API**
3. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** (NOT anon key) → `SUPABASE_SERVICE_ROLE_KEY`

⚠️ **Security Note:** The service_role key has admin access. Keep it secure and never expose it in client-side code.

---

## Step 2: Create Storage Buckets

### Create `user-profiles` Bucket

1. Go to **Storage** in Supabase dashboard
2. Click **New bucket**
3. **Bucket name:** `user-profiles`
4. **Public bucket:** ✅ **YES** (Enable public access)
5. **File size limit:** 5 MB
6. **Allowed MIME types:** 
   - `image/jpeg`
   - `image/jpg`
   - `image/png`
   - `image/webp`
7. Click **Create bucket**

### Create `event-images` Bucket

1. Click **New bucket** again
2. **Bucket name:** `event-images`
3. **Public bucket:** ✅ **YES** (Enable public access)
4. **File size limit:** 5 MB
5. **Allowed MIME types:**
   - `image/jpeg`
   - `image/jpg`
   - `image/png`
   - `image/webp`
6. Click **Create bucket**

---

## Step 3: Configure Storage Policies (RLS)

Supabase uses Row Level Security (RLS) for storage access control. Configure these policies:

### Policy 1: Public Read Access (Both Buckets)

**For `user-profiles` bucket:**

```sql
-- Allow anyone to read files
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'user-profiles');
```

**For `event-images` bucket:**

```sql
-- Allow anyone to read files
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'event-images');
```

### Policy 2: Authenticated Upload (Both Buckets)

**For `user-profiles` bucket:**

```sql
-- Allow authenticated users to upload to their own folder
CREATE POLICY "Authenticated users can upload"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'user-profiles' 
  AND auth.role() = 'authenticated'
);
```

**For `event-images` bucket:**

```sql
-- Allow authenticated users to upload
CREATE POLICY "Authenticated users can upload"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'event-images' 
  AND auth.role() = 'authenticated'
);
```

### Policy 3: Update/Delete (Optional - for future use)

If you need users to update/delete their own files:

```sql
-- For user-profiles: Users can only update/delete their own files
CREATE POLICY "Users can update own files"
ON storage.objects FOR UPDATE
USING (
  bucket_id = 'user-profiles'
  AND auth.role() = 'authenticated'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users can delete own files"
ON storage.objects FOR DELETE
USING (
  bucket_id = 'user-profiles'
  AND auth.role() = 'authenticated'
  AND (storage.foldername(name))[1] = auth.uid()::text
);
```

**Note:** Since we're using service_role key (admin access) for uploads from backend, these policies primarily control direct client-side access. The backend uploads bypass RLS due to service_role privileges.

---

## Step 4: Enable Storage API Access

1. Go to **Storage** → **Policies**
2. Ensure **RLS is enabled** for both buckets (default)
3. Verify the policies above are active

---

## Step 5: Test Configuration

### Test Upload via API

```bash
# Test profile picture upload
curl -X POST "http://localhost:8000/api/auth/complete-profile" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "name=John Doe" \
  -F "birth_date=2000-01-01" \
  -F "gender=male" \
  -F "phone_number=+1234567890" \
  -F "event_interests=[1,2,3]" \
  -F "profile_pictures=@/path/to/image1.jpg" \
  -F "profile_pictures=@/path/to/image2.jpg"
```

### Verify File in Supabase Dashboard

1. Go to **Storage** → `user-profiles`
2. Check that files are uploaded with path: `{user_id}/{unique_id}_{filename}`
3. Click on file to get public URL
4. Verify URL is accessible (should work without authentication)

---

## Configuration Summary

| Setting | Value | Purpose |
|---------|-------|---------|
| **SUPABASE_URL** | `https://xxx.supabase.co` | Supabase project URL |
| **SUPABASE_SERVICE_ROLE_KEY** | `eyJ...` | Service role key (admin access) |
| **Bucket: user-profiles** | Public, 5MB limit | User profile pictures |
| **Bucket: event-images** | Public, 5MB limit | Event cover images |
| **RLS Policies** | Public read, Authenticated upload | Security control |

---

## Security Considerations

1. **Service Role Key Security:**
   - ✅ Keep in server-side environment variables only
   - ❌ Never expose in client code, Git, or logs
   - ✅ Rotate periodically (every 90 days recommended)

2. **Public Buckets:**
   - Files in public buckets are accessible to anyone with the URL
   - Use UUID-based filenames to prevent enumeration
   - Consider adding CDN/CloudFront for additional protection (optional)

3. **File Validation:**
   - Enforced server-side: MIME type, file size, extension
   - Client-side validation is a UX enhancement, not security

4. **Access Control:**
   - Current implementation: Backend uses service_role key (bypasses RLS)
   - Alternative: Use anon key + user JWT tokens (more secure, requires Supabase Auth)
   - Recommendation: Current approach is fine for MVP, consider migrating to user tokens later

---

## Troubleshooting

### Error: "Supabase credentials not configured"

**Solution:** Ensure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set in `.env`

### Error: "Bucket not found"

**Solution:** 
1. Verify bucket names are exactly `user-profiles` and `event-images`
2. Check bucket exists in Supabase dashboard
3. Verify bucket is not deleted

### Error: "Failed to upload file to Supabase"

**Possible causes:**
1. Service role key is invalid or expired
2. Bucket RLS policies blocking upload
3. File size exceeds 5MB limit
4. MIME type not allowed

**Debug steps:**
1. Check Supabase dashboard logs
2. Verify file size and type
3. Test with Supabase client directly

### Files uploaded but URLs return 404

**Solution:**
1. Verify bucket is set to **Public**
2. Check RLS policies allow public read
3. Verify file path in storage matches URL path

---

## File Path Structure

**Profile Pictures:**
```
user-profiles/
  └── {user_id}/
      ├── {uuid}_image1.jpg
      ├── {uuid}_image2.jpg
      └── ...
```

**Event Images:**
```
event-images/
  └── {user_id}/
      ├── {uuid}_cover1.jpg
      ├── {uuid}_cover2.jpg
      └── ...
```

**Benefits:**
- Organized by user/event owner
- UUID prevents filename collisions
- Easy to find/delete user's files if needed

---

## Production Checklist

- [ ] Environment variables configured in production
- [ ] Service role key rotated and secured
- [ ] Both buckets created and configured
- [ ] RLS policies applied correctly
- [ ] File size and MIME type restrictions set
- [ ] Public access enabled for read operations
- [ ] Test uploads working correctly
- [ ] URLs are publicly accessible
- [ ] Error handling tested
- [ ] Logging configured for upload failures

