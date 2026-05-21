# Evolution — Frontend Development Skill

**Purpose:** Build and update Next.js pages and components for Evolution Stables.

**When to use:**
- Creating new admin pages
- Building public marketing pages
- Adding React components
- Integrating with the API
- Implementing auth flows

---

## Workflow

### 1. Create Page

**Location:** `app/src/app/{route}/page.tsx`

**Pattern:**
```tsx
'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

interface Horse {
  microchip: string
  name: string
  foaling_date: string
  sex: string
  colour: string
}

export default function HorsesPage() {
  const [horses, setHorses] = useState<Horse[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/horses').then(data => {
      setHorses(data.horses)
      setLoading(false)
    })
  }, [])

  if (loading) return <div>Loading...</div>

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Horses</h1>
      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2">Name</th>
            <th className="text-left py-2">Microchip</th>
            <th className="text-left py-2">Foaling Date</th>
          </tr>
        </thead>
        <tbody>
          {horses.map(horse => (
            <tr key={horse.microchip} className="border-b">
              <td className="py-2">{horse.name}</td>
              <td className="py-2 font-mono">{horse.microchip}</td>
              <td className="py-2">{horse.foaling_date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

### 2. Create Form

**Pattern:**
```tsx
'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import { useRouter } from 'next/navigation'

export default function HorseCreateForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const formData = new FormData(e.currentTarget)
    const data = Object.fromEntries(formData.entries())

    try {
      await api.post('/horses', data)
      router.push('/admin/horses')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create horse')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="bg-red-50 text-red-800 p-4 rounded">
          {error}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium mb-1">
          Microchip (15 digits)
        </label>
        <input
          name="microchip"
          type="text"
          pattern="[0-9]{15}"
          required
          className="w-full border rounded px-3 py-2"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">
          Name
        </label>
        <input
          name="name"
          type="text"
          required
          className="w-full border rounded px-3 py-2"
        />
      </div>

      {/* ... other fields ... */}

      <button
        type="submit"
        disabled={loading}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Creating...' : 'Create Horse'}
      </button>
    </form>
  )
}
```

### 3. API Client

**Location:** `app/src/lib/api.ts`

**Pattern:**
```ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

export const api = {
  async get(endpoint: string) {
    const res = await fetch(`${API_BASE}${endpoint}`)
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.error || 'Request failed')
    }
    return res.json()
  },

  async post(endpoint: string, data: any) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.error || 'Request failed')
    }
    return res.json()
  },

  async patch(endpoint: string, data: any) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.error || 'Request failed')
    }
    return res.json()
  },

  async delete(endpoint: string) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      const error = await res.json()
      throw new Error(error.error || 'Request failed')
    }
    return res.json()
  },
}
```

### 4. Auth Integration

**Location:** `app/src/lib/auth.ts`

**Pattern:**
```ts
import { initializeApp } from 'firebase/app'
import { getAuth, signInWithEmailAndPassword, signOut } from 'firebase/auth'

const firebaseConfig = JSON.parse(process.env.NEXT_PUBLIC_FIREBASE_CONFIG || '{}')
const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)

export async function login(email: string, password: string) {
  const result = await signInWithEmailAndPassword(auth, email, password)
  return result.user
}

export async function logout() {
  await signOut(auth)
}
```

---

## Component Library

**Use shadcn/ui components** — Don't build from scratch.

**Essential components:**
- `Button` — All buttons
- `Card` — Containers
- `Input` — Form inputs
- `Table` — Data tables
- `Dialog` — Modals
- `Toast` — Notifications

**Install:**
```bash
cd app
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add table
```

---

## Styling

**Tailwind CSS only** — No custom CSS files.

**Patterns:**
```tsx
// Layout
<div className="p-8 max-w-7xl mx-auto">
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

// Typography
<h1 className="text-2xl font-bold mb-4">
<p className="text-gray-600 dark:text-gray-400">

// Interactive
<button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors">
<input className="w-full border rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">

// States
<div className={loading ? 'opacity-50 pointer-events-none' : ''}>
<div className={error ? 'border-red-500' : 'border-gray-300'}>
```

---

## Validation

**Match DNA schemas** — Forms must validate against `dna/schemas/*.json`.

**Pattern:**
```tsx
import { horseSchema } from '@/lib/schemas'

function validateHorse(data: any) {
  const result = horseSchema.safeParse(data)
  if (!result.success) {
    return result.error.errors.map(e => ({
      field: e.path.join('.'),
      message: e.message,
    }))
  }
  return []
}
```

---

## Common Pitfalls

❌ **Never write to Firestore directly** — Use API endpoints only  
❌ **Never use horse name as identifier** — Always use microchip  
❌ **Never skip error handling** — Show user-friendly messages  
❌ **Never hardcode API URLs** — Use `process.env.NEXT_PUBLIC_API_URL`  
❌ **Never bypass auth** — Protect admin routes  

---

## Related Files

- **Pages:** `app/src/app/admin/`, `app/src/app/public/`, `app/src/app/auth/`
- **Lib:** `app/src/lib/api.ts`, `app/src/lib/auth.ts`, `app/src/lib/utils.ts`
- **Schemas:** `dna/schemas/*.json`
- **Components:** `app/src/components/` (shadcn/ui)
- **Styles:** `app/src/app/globals.css`, `app/tailwind.config.ts`

---

## Examples

### Horse List Page
See: `app/src/app/admin/horses/page.tsx`

### Horse Create Form
See: `app/src/app/admin/horses/new/page.tsx`

### Login Page
See: `app/src/app/auth/login/page.tsx`
