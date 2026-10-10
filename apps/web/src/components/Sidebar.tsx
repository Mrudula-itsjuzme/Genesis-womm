import Link from "next/link";
import {
  LayoutDashboard,
  Calendar,
  BookOpen,
  ShieldAlert,
  History,
  FileText,
  Settings,
} from "lucide-react";

export default function Sidebar() {
  const navItems = [
    { label: "Dashboard", href: "/", icon: LayoutDashboard },
    { label: "Tentative Calendar", href: "/calendar", icon: Calendar },
    { label: "Resources", href: "/resources", icon: BookOpen },
    { label: "Policy Assistant", href: "/policy", icon: ShieldAlert },
    { label: "Changes", href: "/changes", icon: History },
    { label: "Reports", href: "/reports", icon: FileText },
    { label: "Settings", href: "/settings", icon: Settings },
  ];

  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col h-full h-screen overflow-y-auto">
      <div className="p-6">
        <h2 className="text-xl font-bold tracking-wider text-rose-500">CampusCue</h2>
      </div>
      <nav className="flex-1 px-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              href={item.href}
              className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-rose-900/50 hover:text-rose-100 transition-colors"
            >
              <Icon className="w-5 h-5 text-gray-400" />
              <span className="font-medium text-sm">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center space-x-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center text-rose-950 text-sm font-bold shadow-sm">
            A
          </div>
          <div>
            <p className="text-sm font-medium">Arjun Admin</p>
            <p className="text-xs text-gray-400">Club Admin</p>
          </div>
        </div>
      </div>
    </div>
  );
}
