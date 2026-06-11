const MARKET_TIME_ZONE = 'Asia/Kolkata';
const OPEN_MINUTES = 9 * 60 + 15;
const CLOSE_MINUTES = 15 * 60 + 30;

const formatter = new Intl.DateTimeFormat('en-US', {
  timeZone: MARKET_TIME_ZONE,
  weekday: 'long',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

export function getMarketStatus(now = new Date()) {
  const parts = formatter.formatToParts(now);
  const part = (type) => parts.find(item => item.type === type)?.value;
  const weekday = part('weekday') || '';
  const hour = Number(part('hour'));
  const minute = Number(part('minute'));
  const totalMinutes = hour * 60 + minute;
  const isWeekend = weekday === 'Saturday' || weekday === 'Sunday';

  if (isWeekend) {
    return {
      open: false,
      text: 'Closed (Weekend)',
      sidebarText: 'MARKET CLOSED',
      color: 'var(--red)',
      detail: 'NSE/BSE closed for weekend',
      timeText: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')} IST`,
    };
  }

  if (totalMinutes < OPEN_MINUTES) {
    return {
      open: false,
      text: 'Pre Open',
      sidebarText: 'MARKET CLOSED',
      color: 'var(--yellow)',
      detail: 'Opens at 09:15 IST',
      timeText: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')} IST`,
    };
  }

  if (totalMinutes <= CLOSE_MINUTES) {
    return {
      open: true,
      text: 'Open',
      sidebarText: 'MARKET OPEN',
      color: 'var(--green)',
      detail: 'Closes at 15:30 IST',
      timeText: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')} IST`,
    };
  }

  return {
    open: false,
    text: 'Closed',
    sidebarText: 'MARKET CLOSED',
    color: 'var(--red)',
    detail: 'Closed after 15:30 IST',
    timeText: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')} IST`,
  };
}
