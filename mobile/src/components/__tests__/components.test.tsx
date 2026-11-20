import { fireEvent, render, screen } from '@testing-library/react-native';
import React from 'react';

import i18n from '@/i18n';

import { CategoryPicker } from '../CategoryPicker';
import { SafetyNotice } from '../SafetyNotice';
import { StatusBadge } from '../StatusBadge';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

test('category picker offers the five SRS categories and reports the choice', async () => {
  const onChange = jest.fn();
  await render(<CategoryPicker value={null} onChange={onChange} />);
  for (const label of ['Open burning', 'Illegal dumping', 'Blocked drainage', 'Medical waste', 'Other pollution']) {
    expect(screen.getByLabelText(label)).toBeTruthy();
  }
  await fireEvent.press(screen.getByTestId('category-MEDICAL_WASTE'));
  expect(onChange).toHaveBeenCalledWith('MEDICAL_WASTE');
});

test('the selected category is announced to screen readers', async () => {
  await render(<CategoryPicker value="OPEN_BURNING" onChange={() => {}} />);
  expect(screen.getByTestId('category-OPEN_BURNING').props.accessibilityState).toMatchObject({
    selected: true,
  });
});

test('safety notice is shown, in Swahili too', async () => {
  await render(<SafetyNotice />);
  expect(screen.getByText(/safe distance/i)).toBeTruthy();
  await i18n.changeLanguage('sw');
  await render(<SafetyNotice />);
  expect(screen.getByText(/umbali salama/i)).toBeTruthy();
});

test('status badges use plain language', async () => {
  await render(<StatusBadge status="QUEUED" />);
  expect(screen.getByText('Waiting to send')).toBeTruthy();
});
