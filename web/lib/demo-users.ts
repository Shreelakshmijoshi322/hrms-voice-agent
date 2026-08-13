export type DemoRole = "employee" | "hr_admin";

export type DemoSession = {
  userId: string;
  role: DemoRole;
  name: string;
  email: string;
};

const DEMO_USERS = [
  {
    email: "maya@people.demo",
    password: "employee123",
    userId: "EMP-1042",
    role: "employee",
    name: "Maya Patel",
  },
  {
    email: "priya@people.demo",
    password: "hradmin123",
    userId: "HR-2001",
    role: "hr_admin",
    name: "Priya Sharma",
  },
] as const;

export function authenticateDemoUser(email: string, password: string): DemoSession | null {
  const user = DEMO_USERS.find(
    (candidate) => candidate.email === email && candidate.password === password,
  );
  if (!user) return null;
  return {
    userId: user.userId,
    role: user.role,
    name: user.name,
    email: user.email,
  };
}
