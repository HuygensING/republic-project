export default function clone<T>(obj: any) : T {
  return JSON.parse(JSON.stringify(obj, replacer), reviver) as T;
}

// Stringify maps to json: https://stackoverflow.com/a/56150320
function replacer(key: any, value: any) {
  if(value instanceof Map) {
    return {
      dataType: 'Map',
      value: Array.from(value.entries()),
    };
  } else {
    return value;
  }
}

// Parse json to maps: https://stackoverflow.com/a/56150320
function reviver(key: any, value: any) {
  if(typeof value === 'object' && value !== null) {
    if (value.dataType === 'Map') {
      return new Map(value.value);
    }
  }
  return value;
}
