import React from 'react';
import styles from './ToggleSwitch.module.css';

export default function ToggleSwitch({ id, isOn, handleToggle, disabled }) {
  return (
    <label htmlFor={id} className={styles.toggleSwitch}>
      <input
        id={id}
        type="checkbox"
        checked={isOn}
        onChange={handleToggle}
        disabled={disabled}
      />
      <span className={styles.slider} />
    </label>
  );
}