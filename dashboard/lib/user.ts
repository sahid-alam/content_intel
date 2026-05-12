export type User = { id: string };

export function getCurrentUser(): User {
  return { id: "self" };
}
