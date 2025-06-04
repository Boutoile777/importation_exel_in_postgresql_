import React, { useState, useEffect, useRef } from 'react';
import { FiUser, FiMail, FiEdit3, FiCheck, FiX } from 'react-icons/fi';

function MonCompte() {
  const [user, setUser] = useState({ nom: "", prenom: "", email: "", avatar: null });
  const [editField, setEditField] = useState(null);
  const [tempValues, setTempValues] = useState({});
  const [successMessage, setSuccessMessage] = useState("");

  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await fetch('http://localhost:5000/auth/me', {
          method: 'GET',
          credentials: 'include',
        });
        const data = await response.json();
        if (response.ok) {
          setUser(data);
          setTempValues(data);  // initialise les valeurs temporaires
        } else {
          console.error('Utilisateur non connecté :', data.error);
        }
      } catch (error) {
        console.error('Erreur de récupération de l’utilisateur :', error);
      }
    };
    fetchUser();
  }, []);

  const handleEditClick = (field) => {
    setEditField(field);
  };

  const handleCancel = () => {
    setTempValues(prev => ({ ...prev, [editField]: user[editField] }));
    setEditField(null);
  };

  const handleSave = () => {
    setEditField(null);
  };

  const hasChanges = () => {
    return ['nom', 'prenom', 'email'].some(field => tempValues[field] !== user[field]);
  };

  const handleApplyChanges = async () => {
    try {
      const response = await fetch("http://localhost:5000/auth/me", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        credentials: "include",
        body: JSON.stringify({
          nom: tempValues.nom,
          prenom: tempValues.prenom,
          email: tempValues.email
        })
      });

     if (!response.ok) {
      throw new Error("Erreur lors de la mise à jour.");
    }

    const updatedUser = await response.json();
    setUser(updatedUser);
    setSuccessMessage("✅ Profil mis à jour avec succès.");

    // Efface le message après 4 secondes
    setTimeout(() => setSuccessMessage(""), 4000);
  } catch (err) {
    console.error(err);
    setSuccessMessage("❌ Échec de la mise à jour du profil.");
    setTimeout(() => setSuccessMessage(""), 4000);
  }
};

  const renderField = (label, fieldKey, value, icon) => {
    const isEditing = editField === fieldKey;
    return (
      <div className="flex flex-col gap-2 bg-white p-5 rounded-xl shadow border">
        <div className="flex items-center gap-3 mb-1">
          {icon}
          <h4 className="text-gray-600 font-medium">{label}</h4>
        </div>
        {!isEditing ? (
          <div className="flex justify-between items-center">
            <p className="text-lg font-semibold text-gray-800">{tempValues[fieldKey]}</p>
            <button
              onClick={() => handleEditClick(fieldKey)}
              className="text-green-600 hover:text-green-800"
              title="Modifier"
            >
              <FiEdit3 size={20} />
            </button>
          </div>
        ) : (
          <>
            <input
              type="text"
              value={tempValues[fieldKey]}
              onChange={(e) => setTempValues({ ...tempValues, [fieldKey]: e.target.value })}
              className="input-style"
            />
            <div className="flex gap-2 mt-2">
              <button onClick={handleSave} className="text-green-600 hover:text-green-800">
                <FiCheck size={20} />
              </button>
              <button onClick={handleCancel} className="text-red-500 hover:text-red-700">
                <FiX size={20} />
              </button>
            </div>
          </>
        )}
      </div>
    );
  };

  return (
    <div className="w-full min-h-screen bg-gray-50 flex flex-col items-center px-4 py-10">
      <h2 className="text-4xl font-bold text-green-700 mb-8">Mon compte</h2>

      <div className="w-full max-w-4xl bg-white rounded-3xl shadow-xl p-6 md:p-10 flex flex-col md:flex-row gap-10 items-center md:items-start">
        {/* Avatar */}
        <div className="flex flex-col items-center gap-4">
          <div className="w-32 h-32 md:w-40 md:h-40 rounded-full overflow-hidden border-4 border-green-100 shadow-md flex items-center justify-center bg-gray-100">
            {user.avatar ? (
              <img src={user.avatar} alt="Avatar utilisateur" className="object-cover w-full h-full" />
            ) : (
              <FiUser className="text-green-600 w-20 h-20 md:w-24 md:h-24 p-6" />
            )}
          </div>
        </div>

        {/* Infos */}
        <div className="flex flex-col flex-grow gap-6 w-full max-w-md">
          {renderField("Nom", "nom", user.nom, <FiUser size={24} className="text-green-600" />)}
          {renderField("Prénom", "prenom", user.prenom, <FiUser size={24} className="text-green-600" />)}
          {renderField("Adresse email", "email", user.email, <FiMail size={24} className="text-green-600" />)}

          {hasChanges() && (
              <>
                <button
                  onClick={handleApplyChanges}
                  className="mt-4 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition"
                >
                  Lancer les modifications
                </button>
                {successMessage && (
                  <p className="mt-3 text-center text-green-600 font-semibold">{successMessage}</p>
                )}
              </>
            )}
        </div>
      </div>
    </div>
  );
}

export default MonCompte;
