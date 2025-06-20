// src/components/Header.js
import './Header.css'; // Crie este arquivo CSS depois

const Header = () => {
  return (
    <header className="header">
      <div className="header-logo">
        <img src="/logo.jpg" alt="F1App Logo" style={{ height: '50px' }} /> {/* Certifique-se de que o logo esteja em public/logo.svg */}
        <h1>F1App</h1>
      </div>
      <nav className="header-nav">
        <ul>
          <li><a href="#home">Início</a></li>
          <li><a href="#teams">Equipes</a></li>
          <li><a href="#drivers">Pilotos</a></li>
          <li><a href="#results">Resultados</a></li>
          <li><a href="#standings">Classificação</a></li>
          <li><a href="#tracks">Autódromos</a></li>
          <li><a href="#stats">Estatísticas</a></li>
        </ul>
      </nav>
      <div className="header-quick-actions">
        {/* Ex: Busca, link para Próxima Corrida */}
        <input type="text" placeholder="Buscar..." />
        <button>Próxima Corrida</button>
      </div>
    </header>
  );
};

export default Header;