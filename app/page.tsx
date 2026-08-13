import { redirect } from "next/navigation";

import { RoleDashboard } from "@/web/components/role-dashboard";
import { readDemoSession } from "@/web/lib/server-session";

export default async function HomePage() {
  const session = await readDemoSession();
  if (!session) redirect("/login");
  return <RoleDashboard session={session} />;
}
