---
name: create-landing
description: Generate a beautiful, conversion-optimized landing page with hero, features, CTA sections
argument-hint: [product-name] [optional:tagline or description]
context: fork
agent: frontend-engineer
allowed-tools: Read, Write, Glob, Grep, Bash(npm:*)
---

# Landing Page Generator

Create a stunning landing page for: **$ARGUMENTS**

## Page Structure

### 1. Hero Section
- Compelling headline (benefit-focused, not feature-focused)
- Subheadline explaining the value proposition
- Primary CTA button (high contrast, action-oriented text)
- Optional: Hero image, demo video, or animation
- Social proof snippet (e.g., "Trusted by 10,000+ users")

### 2. Problem/Solution Section
- Identify the pain point your audience faces
- Present your product as the solution
- Use relatable language

### 3. Features Section (3-4 key features)
For each feature:
- Icon or illustration
- Short, punchy headline
- 1-2 sentence description
- Focus on benefits, not just features

### 4. Social Proof Section
- Testimonials with photos and names
- Company logos ("As seen in..." or "Trusted by...")
- Key metrics or statistics

### 5. How It Works (optional)
- 3-step process
- Simple icons or illustrations
- Clear, concise copy

### 6. Pricing Section (optional)
- Clear pricing tiers
- Feature comparison
- Highlight recommended plan
- CTA on each tier

### 7. FAQ Section
- Address common objections
- Use accordion/collapsible format
- 5-7 questions

### 8. Final CTA Section
- Restate the main value proposition
- Strong call-to-action
- Reduce friction (no credit card required, free trial, etc.)

### 9. Footer
- Navigation links
- Social media links
- Legal links (Privacy, Terms)
- Copyright

## Design Principles

1. **Visual Hierarchy**: Guide the eye with size, color, spacing
2. **White Space**: Don't crowd elements
3. **Consistent Colors**: Use 2-3 colors max from project palette
4. **Mobile First**: Responsive design, stack elements on mobile
5. **Fast Loading**: Optimize images, lazy load below-fold content

## Implementation

1. Check existing project styles (Tailwind classes, CSS variables)
2. Create reusable section components if they don't exist
3. Use semantic HTML (section, article, nav, footer)
4. Add smooth scroll behavior for anchor links
5. Ensure accessibility (contrast, focus states, alt text)

## Copy Guidelines

- Headlines: 6-12 words
- Subheadlines: 15-25 words
- Body text: Short paragraphs, bullet points
- CTAs: Action verbs ("Get Started", "Try Free", "See Demo")
