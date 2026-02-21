# Agent instructions

## Frontend styling

Use **Tailwind CSS** and **shadcn/ui** by default for all UI work:

- Style with Tailwind utility classes (`className="..."`).
- Use shadcn components from `@/components/ui` (e.g. `Button`, `Card`, `Input`, `Dialog`) instead of building custom primitives or adding other UI libraries.

## How to add an API endpoint and generate type-safe frontend code

1. **Add the endpoint in the API** (`api/index.py`):

   - Define a Pydantic **response model** (subclass of `BaseModel`) for the JSON body.
   - Add a route with `@app.get(...)` or `@app.post(...)`, set `response_model=` to that model, and implement the handler.

   Example:

   ```python
   class MyResponse(BaseModel):
       value: str

   @app.get("/my/route", response_model=MyResponse)
   def my_endpoint() -> MyResponse:
       return MyResponse(value="ok")
   ```

2. **Export the OpenAPI spec and generate the frontend code**  
   The frontend client is generated from `api/openapi.json`. After changing the API, regenerate it:

   - From repo root: `npm run api:gen` (this runs the export and then Orval).

3. **Use the generated code in the UI**
   - Import the React Query hook from `@/api/generated/endpoints`, e.g. `useGetMyRouteGet` (name is derived from the path and method).
   - Import response types from `@/api/generated/schemas` if needed.
   - Call the hook in your component; it returns `{ data, isLoading, error, refetch }` (and the response is typed).

Summary: **Edit `api/index.py` → run `npm run api:gen` → import and use the new hook/schemas in the UI.**

**Note:** The generated client (`ui/src/api/generated/`) is not committed. After cloning or after any API change, you must run `npm run api:gen` so the frontend has the latest endpoints and types.
