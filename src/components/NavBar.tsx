// src/components/NavBar.tsx
import React from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import { useCart } from "../stores/cartStore";
import { authApi } from "../api/auth";

export default function NavBar() {
  // Hooks must be top-level (not inside callbacks)
  const count = useCart((s) => s.count());
  const location = useLocation();
  const navigate = useNavigate();

  const [email, setEmail] = React.useState("dev@example.com");
  const [pass, setPass] = React.useState("password");
  const [loggedIn, setLoggedIn] = React.useState<boolean>(
    !!localStorage.getItem("auth_token")
  );

  // helper to apply a minimal active style (you can style with CSS classes instead)
  const linkStyle = ({ isActive }: { isActive: boolean }) => ({
    marginRight: 12,
    textDecoration: isActive ? "underline" : "none",
  });

  async function quickLogin() {
    try {
      await authApi.login(email, pass);
      // update local state so component re-renders and shows Logout
      setLoggedIn(true);
      alert("Logged in (dev)");
    } catch (e: any) {
      alert(e?.message || "Login failed");
    }
  }

  function doLogout() {
    // remove token, update state, and navigate to home
    localStorage.removeItem("auth_token");
    setLoggedIn(false);
    navigate("/");
  }

  return (
    <nav
      style={{
        padding: 12,
        borderBottom: "1px solid #eee",
        marginBottom: 12,
        display: "flex",
        gap: 12,
        alignItems: "center",
      }}
    >
      <div style={{ flex: 1 }}>
        <NavLink to="/" style={linkStyle}>
          Home
        </NavLink>
        <NavLink to="/catalogue" style={linkStyle}>
          Catalogue
        </NavLink>
        <NavLink to="/cart" style={linkStyle}>
          Cart ({count})
        </NavLink>
        <NavLink to="/admin" style={linkStyle}>
          Admin
        </NavLink>
      </div>

      <div>
        {loggedIn ? (
          <button onClick={doLogout}>Logout</button>
        ) : (
          <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
            <input
              placeholder="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{ width: 160 }}
            />
            <input
              placeholder="password"
              type="password"
              value={pass}
              onChange={(e) => setPass(e.target.value)}
              style={{ width: 120 }}
            />
            <button onClick={quickLogin}>Dev Login</button>
          </span>
        )}
      </div>
    </nav>
  );
}
