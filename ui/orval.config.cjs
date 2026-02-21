/** @type {import('orval').DefineConfig} */
module.exports = {
  api: {
    input: {
      target: "../api/openapi.json",
    },
    output: {
      mode: "single",
      target: "src/api/generated/endpoints.ts",
      schemas: "src/api/generated/schemas",
      client: "react-query",
      clean: true,
      baseUrl: "/api",
      override: {
        mutator: {
          path: "./src/api/mutator/custom-fetch.ts",
          name: "customFetch",
        },
        query: {
          useQuery: true,
          useMutation: true,
          options: {
            staleTime: 30_000,
          },
        },
      },
    },
  },
};
