---
name: quick-prototype
description: Rapidly build a working prototype/MVP with minimal setup - perfect for hackathons and quick demos
argument-hint: [idea-description]
context: fork
agent: general-purpose
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Quick Prototype Builder

Build a working prototype for: **$ARGUMENTS**

## Philosophy

- **Speed over perfection**: Get something working FAST
- **Fake it till you make it**: Mock data, hardcoded values are OK
- **Focus on the "wow"**: Build the core feature that demonstrates value
- **Skip the boring stuff**: No auth, no database (unless essential)

## Approach

### 1. Identify the Core Feature
- What's the ONE thing this prototype must demonstrate?
- What would make someone say "wow, that's cool"?
- Cut everything else ruthlessly

### 2. Choose the Fastest Path

**For Web Apps:**
- Next.js with App Router (if project exists)
- Single HTML file with Tailwind CDN (for quick demos)
- Use existing UI components in the project

**For Data/API:**
- Hardcode sample data in a JSON file
- Use free public APIs when possible
- Mock API responses

**For AI Features:**
- Use existing API keys from .env
- Keep prompts simple and direct
- Cache responses during demo

### 3. Build Order

```
1. Static UI shell (5 min)
   └── Layout, navigation, placeholder content

2. Core interaction (15 min)
   └── The main feature that shows the idea works

3. Polish the happy path (10 min)
   └── Make the demo flow smooth

4. Add "fake" depth (5 min)
   └── Loading states, transitions, sample data
```

### 4. Shortcuts to Use

| Instead of... | Do this... |
|--------------|------------|
| Real database | JSON file or localStorage |
| User auth | Hardcoded user object |
| File uploads | Pre-loaded sample files |
| Payment | "Payment successful" mock |
| Email sending | Console.log + alert |
| Complex forms | Minimal fields only |

### 5. Make It Demo-Ready

- Add sample data that tells a story
- Include loading states (they look professional)
- Add one subtle animation
- Test the exact demo flow 3 times
- Have a "reset" button if state gets messy

## Output

Create:
1. Working prototype of the core feature
2. Sample data that demonstrates value
3. Brief README with:
   - What it does
   - How to run it
   - What's real vs mocked

## Remember

> "If you're not embarrassed by the first version, you shipped too late."

Get it working. Get feedback. Iterate.
