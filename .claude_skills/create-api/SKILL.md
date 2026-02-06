---
name: create-api
description: Generate a REST API endpoint with validation, error handling, types, and documentation
argument-hint: [endpoint-name] [method:GET|POST|PUT|DELETE] [optional:description]
context: fork
agent: elite-backend-engineer
allowed-tools: Read, Write, Glob, Grep, Bash
---

# API Endpoint Generator

Create a production-ready API endpoint: **$ARGUMENTS**

## Steps

1. **Analyze existing API structure**:
   - Check `src/app/api/`, `pages/api/`, or `routes/` for patterns
   - Identify validation library (zod, yup, joi)
   - Find error handling patterns
   - Check authentication/middleware setup

2. **Create the endpoint** with:

### Request Handling
```typescript
// Type-safe request body/params
interface RequestBody {
  // Define expected fields
}

// Validation schema
const schema = z.object({
  // Zod schema matching RequestBody
});
```

### Response Types
```typescript
interface SuccessResponse {
  success: true;
  data: // response data type
}

interface ErrorResponse {
  success: false;
  error: string;
  code?: string;
}
```

### Error Handling
- 400: Validation errors (with field-level details)
- 401: Unauthorized
- 403: Forbidden
- 404: Not found
- 500: Internal error (log details, return generic message)

3. **Implementation pattern**:
```typescript
export async function POST(request: Request) {
  try {
    // 1. Parse and validate input
    const body = await request.json();
    const validated = schema.parse(body);

    // 2. Business logic
    const result = await doSomething(validated);

    // 3. Return success response
    return Response.json({ success: true, data: result });

  } catch (error) {
    // 4. Handle errors appropriately
    if (error instanceof z.ZodError) {
      return Response.json({ success: false, error: 'Validation failed', details: error.errors }, { status: 400 });
    }
    console.error('API Error:', error);
    return Response.json({ success: false, error: 'Internal server error' }, { status: 500 });
  }
}
```

4. **Security checklist**:
- [ ] Input validation on all user data
- [ ] Rate limiting consideration
- [ ] Authentication check if needed
- [ ] No sensitive data in error messages
- [ ] SQL injection prevention (parameterized queries)

5. **Add inline documentation** for the endpoint's purpose and usage.
